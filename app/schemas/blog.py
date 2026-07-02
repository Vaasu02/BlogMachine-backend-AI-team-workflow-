from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BlogGenerateRequest(BaseModel):
    topic: str


class BlogResponse(BaseModel):
    id: str
    topic: str
    title: Optional[str] = None
    content: Optional[str] = None
    meta_description: Optional[str] = None
    tags: Optional[str] = None
    subject: Optional[str] = None
    gs_paper: Optional[str] = None
    seo_score: Optional[int] = None
    status: str
    mcqs: Optional[str] = None
    images: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BlogListResponse(BaseModel):
    blogs: list[BlogResponse]
    total: int
