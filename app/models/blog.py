import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Blog(Base):
    __tablename__ = "blogs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = Column(String(500), nullable=False)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    meta_description = Column(String(300), nullable=True)
    tags = Column(String(500), nullable=True)
    subject = Column(String(100), nullable=True)
    gs_paper = Column(String(10), nullable=True)
    seo_score = Column(Integer, nullable=True)
    status = Column(String(50), default="pending")
    mcqs = Column(Text, nullable=True)
    images = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    logs = relationship("AgentLog", back_populates="blog", cascade="all, delete-orphan")
