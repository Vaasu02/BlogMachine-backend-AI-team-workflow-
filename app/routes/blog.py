import hashlib

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.blog import Blog
from app.models.topic import Topic
from app.models.agent_log import AgentLog
from app.schemas.blog import BlogGenerateRequest, BlogResponse, BlogListResponse
from app.orchestrator.state_machine import run_blog_pipeline

router = APIRouter(prefix="/api/blog", tags=["blog"])


def get_topic_hash(topic: str) -> str:
    normalized = topic.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


@router.post("/generate", response_model=BlogResponse)
async def generate_blog(
    request: BlogGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    topic_hash = get_topic_hash(request.topic)
    existing_topic = db.query(Topic).filter(Topic.hash == topic_hash).first()
    if existing_topic:
        existing_blog = db.query(Blog).filter(
            Blog.topic == existing_topic.title,
            Blog.status == "completed",
        ).first()
        if existing_blog:
            raise HTTPException(
                status_code=409,
                detail=f"A blog on this topic already exists (id: {existing_blog.id})",
            )

    topic_record = Topic(title=request.topic.strip(), hash=topic_hash)
    db.add(topic_record)

    blog = Blog(topic=request.topic.strip(), status="pending")
    db.add(blog)
    db.commit()
    db.refresh(blog)

    background_tasks.add_task(run_blog_pipeline, blog.id, request.topic.strip())

    return blog


@router.get("/{blog_id}", response_model=BlogResponse)
async def get_blog(blog_id: str, db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog


@router.get("s/", response_model=BlogListResponse)
async def list_blogs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    blogs = db.query(Blog).order_by(Blog.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(Blog).count()
    return BlogListResponse(blogs=blogs, total=total)


@router.delete("/{blog_id}")
async def delete_blog(blog_id: str, db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    db.delete(blog)
    db.commit()
    return {"detail": "Blog deleted"}


@router.get("/{blog_id}/logs")
async def get_blog_logs(blog_id: str, db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    logs = db.query(AgentLog).filter(AgentLog.blog_id == blog_id).order_by(AgentLog.timestamp).all()

    return [
        {
            "id": log.id,
            "agent_name": log.agent_name,
            "state": log.state,
            "status": log.status,
            "input_data": log.input_data,
            "output_data": log.output_data,
            "feedback": log.feedback,
            "retry_count": log.retry_count,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]
