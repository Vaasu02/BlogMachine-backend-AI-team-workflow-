import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    blog_id = Column(String, ForeignKey("blogs.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    status = Column(String(50), default="running")
    timestamp = Column(DateTime, default=utc_now)

    blog = relationship("Blog", back_populates="logs")
