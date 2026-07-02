import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.blog import Blog
from app.models.agent_log import AgentLog
from app.orchestrator.states import (
    BlogState,
    TRANSITIONS,
    AGENT_MAP,
    PROGRESS_MAP,
)
from app.orchestrator.event_bus import event_bus
from app.agents.base import AgentResult
from app.config import settings

logger = logging.getLogger(__name__)


class PipelineContext:
    """Holds all data flowing between agents during a single blog generation."""

    def __init__(self, blog_id: str, topic: str):
        self.blog_id = blog_id
        self.topic = topic
        self.research = {}
        self.narrative = {}
        self.draft = {}
        self.fact_check = {}
        self.humanized = {}
        self.seo = {}
        self.mcqs = {}
        self.images = {}

    def get_input_for_state(self, state: BlogState) -> dict:
        if state == BlogState.TOPIC_RESEARCH:
            return {"topic": self.topic}
        elif state == BlogState.NARRATIVE_PLANNING:
            return {"topic": self.topic, "research": self.research}
        elif state == BlogState.WRITING:
            return {
                "topic": self.topic,
                "research": self.research,
                "narrative": self.narrative,
                "feedback": self.fact_check.get("feedback"),
            }
        elif state == BlogState.FACT_CHECKING:
            return {"draft": self.draft, "topic": self.topic}
        elif state == BlogState.HUMANIZING:
            return {
                "draft": self.draft,
                "feedback": self.seo.get("feedback"),
            }
        elif state == BlogState.SEO_CHECK:
            return {"content": self.humanized, "topic": self.topic}
        elif state == BlogState.MCQ_GENERATION:
            return {"content": self.humanized, "topic": self.topic}
        elif state == BlogState.IMAGE_SELECTION:
            return {"topic": self.topic, "title": self.humanized.get("title", self.topic)}
        return {}

    def store_output(self, state: BlogState, output: dict):
        if state == BlogState.TOPIC_RESEARCH:
            self.research = output
        elif state == BlogState.NARRATIVE_PLANNING:
            self.narrative = output
        elif state == BlogState.WRITING:
            self.draft = output
        elif state == BlogState.FACT_CHECKING:
            self.fact_check = output
        elif state == BlogState.HUMANIZING:
            self.humanized = output
        elif state == BlogState.SEO_CHECK:
            self.seo = output
        elif state == BlogState.MCQ_GENERATION:
            self.mcqs = output
        elif state == BlogState.IMAGE_SELECTION:
            self.images = output


def get_agent_instance(state: BlogState):
    from app.agents.topic_scout import TopicScoutAgent
    from app.agents.narrative import NarrativePlannerAgent
    from app.agents.writer import ContentWriterAgent
    from app.agents.fact_checker import FactCheckerAgent
    from app.agents.humanizer import HumanizerAgent
    from app.agents.seo_optimizer import SEOOptimizerAgent
    from app.agents.mcq_generator import MCQGeneratorAgent
    from app.agents.image_selector import ImageSelectorAgent

    agent_classes = {
        BlogState.TOPIC_RESEARCH: TopicScoutAgent,
        BlogState.NARRATIVE_PLANNING: NarrativePlannerAgent,
        BlogState.WRITING: ContentWriterAgent,
        BlogState.FACT_CHECKING: FactCheckerAgent,
        BlogState.HUMANIZING: HumanizerAgent,
        BlogState.SEO_CHECK: SEOOptimizerAgent,
        BlogState.MCQ_GENERATION: MCQGeneratorAgent,
        BlogState.IMAGE_SELECTION: ImageSelectorAgent,
    }

    agent_class = agent_classes.get(state)
    if agent_class:
        return agent_class()
    return None


async def emit_event(blog_id: str, agent_name: str, state: BlogState, status: str, message: str, feedback_loop: dict = None):
    event = {
        "blog_id": blog_id,
        "current_agent": agent_name,
        "state": state.value,
        "status": status,
        "message": message,
        "progress": PROGRESS_MAP.get(state, 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feedback_loop": feedback_loop,
    }
    await event_bus.publish(blog_id, event)


def log_agent_activity(db: Session, blog_id: str, agent_name: str, state: str, input_data: dict, output_data: dict = None, feedback: str = None, retry_count: int = 0, status: str = "running"):
    log = AgentLog(
        blog_id=blog_id,
        agent_name=agent_name,
        state=state,
        input_data=json.dumps(input_data, default=str),
        output_data=json.dumps(output_data, default=str) if output_data else None,
        feedback=feedback,
        retry_count=retry_count,
        status=status,
    )
    db.add(log)
    db.commit()


def get_next_state(current: BlogState, result: AgentResult) -> BlogState:
    """Determine the next state based on agent result and feedback."""
    allowed = TRANSITIONS.get(current, [])

    if not result.success:
        return BlogState.FAILED

    if current == BlogState.FACT_CHECKING:
        if result.output.get("verified") is False:
            return BlogState.WRITING
        return BlogState.HUMANIZING

    elif current == BlogState.HUMANIZING:
        return BlogState.SEO_CHECK

    elif current == BlogState.SEO_CHECK:
        seo_score = result.output.get("seo_score", 0)
        if seo_score < 70:
            return BlogState.HUMANIZING
        return BlogState.MCQ_GENERATION

    for state in allowed:
        if state != BlogState.FAILED:
            return state

    return BlogState.FAILED


PIPELINE_ORDER = [
    BlogState.TOPIC_RESEARCH,
    BlogState.NARRATIVE_PLANNING,
    BlogState.WRITING,
    BlogState.FACT_CHECKING,
    BlogState.HUMANIZING,
    BlogState.SEO_CHECK,
    BlogState.MCQ_GENERATION,
    BlogState.IMAGE_SELECTION,
]


async def run_blog_pipeline(blog_id: str, topic: str):
    """Main orchestrator — runs the blog generation pipeline with feedback loops."""
    db = SessionLocal()
    context = PipelineContext(blog_id, topic)
    retry_counts = {
        "fact_check_to_writer": 0,
        "seo_to_humanizer": 0,
    }
    max_retries = settings.MAX_FEEDBACK_RETRIES

    try:
        db.query(Blog).filter(Blog.id == blog_id).update({"status": "running"})
        db.commit()

        current_state = BlogState.TOPIC_RESEARCH

        while current_state not in (BlogState.COMPLETED, BlogState.FAILED):
            agent_name = AGENT_MAP.get(current_state, "unknown")
            agent = get_agent_instance(current_state)

            if not agent:
                await emit_event(blog_id, agent_name, current_state, "failed", f"No agent found for state: {current_state.value}")
                current_state = BlogState.FAILED
                break

            print(f"[PIPELINE] Starting {agent_name}...")
            await emit_event(blog_id, agent_name, current_state, "running", f"{agent_name} is working...")

            input_data = context.get_input_for_state(current_state)
            log_agent_activity(db, blog_id, agent_name, current_state.value, input_data)

            try:
                result = await agent.execute(input_data)
            except Exception as e:
                print(f"[PIPELINE] {agent_name} FAILED: {str(e)[:200]}")
                await emit_event(blog_id, agent_name, current_state, "error", f"{agent_name} failed: {str(e)}")
                log_agent_activity(db, blog_id, agent_name, current_state.value, input_data, status="error")
                current_state = BlogState.FAILED
                break

            if result.success:
                context.store_output(current_state, result.output)
                log_agent_activity(db, blog_id, agent_name, current_state.value, input_data, result.output, status="completed")
                print(f"[PIPELINE] {agent_name} COMPLETED")
                await emit_event(blog_id, agent_name, current_state, "completed", f"{agent_name} finished successfully.")
            else:
                print(f"[PIPELINE] {agent_name} REJECTED: {result.feedback}")
                log_agent_activity(db, blog_id, agent_name, current_state.value, input_data, result.output, feedback=result.feedback, status="rejected")

            next_state = get_next_state(current_state, result)

            # Handle feedback loops with retry limits
            if current_state == BlogState.FACT_CHECKING and next_state == BlogState.WRITING:
                retry_counts["fact_check_to_writer"] += 1
                if retry_counts["fact_check_to_writer"] > max_retries:
                    await emit_event(blog_id, agent_name, current_state, "warning", f"Max retries reached for fact-check loop. Proceeding with best attempt.")
                    next_state = BlogState.HUMANIZING
                else:
                    context.fact_check["feedback"] = result.feedback
                    await emit_event(
                        blog_id, agent_name, current_state, "feedback",
                        f"Fact checker rejected draft. Sending back to writer (attempt {retry_counts['fact_check_to_writer']}/{max_retries})",
                        feedback_loop={
                            "active": True,
                            "from": "fact_checker",
                            "to": "content_writer",
                            "reason": result.feedback,
                            "retry_count": retry_counts["fact_check_to_writer"],
                        },
                    )

            elif current_state == BlogState.SEO_CHECK and next_state == BlogState.HUMANIZING:
                retry_counts["seo_to_humanizer"] += 1
                if retry_counts["seo_to_humanizer"] > max_retries:
                    await emit_event(blog_id, agent_name, current_state, "warning", f"Max retries reached for SEO loop. Proceeding with current content.")
                    next_state = BlogState.MCQ_GENERATION
                else:
                    context.seo["feedback"] = result.feedback
                    await emit_event(
                        blog_id, agent_name, current_state, "feedback",
                        f"SEO score too low. Sending back to humanizer (attempt {retry_counts['seo_to_humanizer']}/{max_retries})",
                        feedback_loop={
                            "active": True,
                            "from": "seo_optimizer",
                            "to": "humanizer",
                            "reason": result.feedback,
                            "retry_count": retry_counts["seo_to_humanizer"],
                        },
                    )

            current_state = next_state

        # Finalize blog in DB
        if current_state == BlogState.COMPLETED:
            db.query(Blog).filter(Blog.id == blog_id).update({
                "status": "completed",
                "title": context.humanized.get("title", context.draft.get("title", topic)),
                "content": context.humanized.get("content", ""),
                "meta_description": context.seo.get("meta_description", ""),
                "tags": json.dumps(context.seo.get("tags", [])),
                "subject": context.narrative.get("subject", ""),
                "gs_paper": context.narrative.get("gs_paper", ""),
                "seo_score": context.seo.get("seo_score", 0),
                "mcqs": json.dumps(context.mcqs),
                "images": json.dumps(context.images),
            })
            db.commit()
            await emit_event(blog_id, "system", BlogState.COMPLETED, "completed", "Blog generation completed successfully!")
        else:
            db.query(Blog).filter(Blog.id == blog_id).update({"status": "failed"})
            db.commit()
            await emit_event(blog_id, "system", BlogState.FAILED, "failed", "Blog generation failed.")

    except Exception as e:
        db.query(Blog).filter(Blog.id == blog_id).update({"status": "failed"})
        db.commit()
        await emit_event(blog_id, "system", BlogState.FAILED, "failed", f"Pipeline error: {str(e)}")
    finally:
        db.close()
