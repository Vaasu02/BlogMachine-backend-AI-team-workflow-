from celery import Celery
from app.config import settings

celery_app = Celery(
    "blog_machine",
    broker=settings.REDIS_URL, #connect to redis as the message broker 
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=1,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
)

celery_app.autodiscover_tasks(["app.tasks"])
