import asyncio
import traceback

from app.celery_app import celery_app
from app.orchestrator.state_machine import run_blog_pipeline
from app.database import SessionLocal
from app.models.blog import Blog


@celery_app.task(name="generate_blog", bind=True, max_retries=0)
def generate_blog_task(self, blog_id: str, topic: str):
    """Celery task that runs the blog generation pipeline."""
    try:
        asyncio.run(run_blog_pipeline(blog_id, topic))
        db = SessionLocal()
        try:
            blog = db.query(Blog).filter(Blog.id == blog_id).first()
            actual_status = blog.status if blog else "failed"
        finally:
            db.close()
        return {"blog_id": blog_id, "status": actual_status}
    except Exception as e:
        print(f"[CELERY TASK ERROR] blog_id={blog_id}: {str(e)}")
        traceback.print_exc()
        return {"blog_id": blog_id, "status": "failed", "error": str(e)}
