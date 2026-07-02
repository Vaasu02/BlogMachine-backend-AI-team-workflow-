from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AgentEvent(BaseModel):
    blog_id: str
    current_agent: str
    state: str
    status: str
    message: str
    progress: int
    timestamp: datetime
    feedback_loop: Optional[dict] = None
