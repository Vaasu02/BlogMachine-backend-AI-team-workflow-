import asyncio
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models.blog import Blog
from app.models.agent_log import AgentLog
from app.orchestrator.event_bus import event_bus
from app.orchestrator.states import PROGRESS_MAP, BlogState

router = APIRouter(prefix="/api/blog", tags=["stream"])

STATE_TO_PROGRESS = {s.value: p for s, p in PROGRESS_MAP.items()}


@router.get("/stream/{blog_id}")
async def stream_blog_status(blog_id: str, db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()

    async def event_generator():
        if not blog:
            yield {
                "event": "error",
                "data": json.dumps({"message": "Blog not found"}),
            }
            return

        if blog.status in ("completed", "failed"):
            logs = db.query(AgentLog).filter(AgentLog.blog_id == blog_id).order_by(AgentLog.timestamp).all()
            for log in logs:
                yield {
                    "event": log.status,
                    "data": json.dumps({
                        "blog_id": blog_id,
                        "current_agent": log.agent_name,
                        "state": log.state,
                        "status": log.status,
                        "message": f"{log.agent_name} — {log.status}",
                        "progress": STATE_TO_PROGRESS.get(log.state, 0),
                        "timestamp": log.timestamp.isoformat(),
                        "feedback_loop": {
                            "active": True,
                            "from": log.agent_name,
                            "reason": log.feedback,
                            "retry_count": log.retry_count,
                        } if log.feedback else None,
                    }),
                }
            yield {
                "event": blog.status,
                "data": json.dumps({
                    "blog_id": blog_id,
                    "current_agent": "system",
                    "state": blog.status,
                    "status": blog.status,
                    "message": f"Blog generation {blog.status}.",
                    "progress": 100 if blog.status == "completed" else 0,
                    "timestamp": blog.updated_at.isoformat() if blog.updated_at else "",
                }),
            }
            return

        # Subscribe to live events
        queue = event_bus.subscribe(blog_id)

        # Replay any events that already happened before we subscribed
        existing_logs = db.query(AgentLog).filter(AgentLog.blog_id == blog_id).order_by(AgentLog.timestamp).all()
        for log in existing_logs:
            yield {
                "event": log.status,
                "data": json.dumps({
                    "blog_id": blog_id,
                    "current_agent": log.agent_name,
                    "state": log.state,
                    "status": log.status,
                    "message": f"{log.agent_name} — {log.status}",
                    "progress": STATE_TO_PROGRESS.get(log.state, 0),
                    "timestamp": log.timestamp.isoformat(),
                    "feedback_loop": {
                        "active": True,
                        "from": log.agent_name,
                        "reason": log.feedback,
                        "retry_count": log.retry_count,
                    } if log.feedback else None,
                }),
            }

        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                event_type = event.get("status", "state_update")
                yield {
                    "event": event_type,
                    "data": json.dumps(event),
                }
                if event.get("current_agent") == "system" and event.get("status") in ("completed", "failed"):
                    break
        except asyncio.TimeoutError:
            yield {
                "event": "timeout",
                "data": json.dumps({"message": "Stream timed out after 5 minutes"}),
            }
        finally:
            event_bus.unsubscribe(blog_id, queue)

    return EventSourceResponse(event_generator())
