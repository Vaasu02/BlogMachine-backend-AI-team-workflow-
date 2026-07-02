from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, SessionLocal
from app.models.blog import Blog
from app.models.agent_log import AgentLog  # noqa: F401
from app.routes.blog import router as blog_router
from app.routes.stream import router as stream_router


def cleanup_stale_blogs():
    db = SessionLocal()
    try:
        stale = db.query(Blog).filter(Blog.status.in_(["pending", "generating", "running"])).all()
        for blog in stale:
            blog.status = "failed"
        db.commit()
        if stale:
            print(f"[STARTUP] Marked {len(stale)} stale blog(s) as failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cleanup_stale_blogs()
    yield


app = FastAPI(title="Blog Machine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(blog_router)
app.include_router(stream_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "blog-machine"}
