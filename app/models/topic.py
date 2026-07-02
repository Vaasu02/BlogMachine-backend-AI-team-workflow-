import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Topic(Base):
    __tablename__ = "topics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    hash = Column(String(64), nullable=True)
    used_at = Column(DateTime, default=utc_now)
