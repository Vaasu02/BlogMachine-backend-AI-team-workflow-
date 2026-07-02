# Blog Machine — Backend

AI-powered blog generation pipeline using a multi-agent team architecture with real-time state visibility.

## Tech Stack

- **Framework:** FastAPI (Python 3.11+)
- **LLM:** Groq (Llama 3.1 70B)
- **Web Search:** Tavily
- **Images:** Pexels API
- **Database:** SQLAlchemy + SQLite
- **Real-time:** Server-Sent Events (SSE)

## Architecture

The backend uses a custom state machine that orchestrates 8 specialized AI agents:

```
Topic Scout → Narrative Planner → Content Writer → Fact Checker → Humanizer → SEO Optimizer → MCQ Generator → Image Selector
                                       ↑                |              ↑              |
                                       └── feedback ────┘              └── feedback ──┘
```

Each agent transition emits SSE events for real-time UI visibility. Feedback loops have a max retry limit of 3 to prevent infinite cycles.

## Setup

```bash
cd backend
python -m venv venv

# Windows
source venv/Scripts/activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the backend directory:

```
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
PEXELS_API_KEY=your_pexels_api_key
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/blog/generate` | Start blog generation |
| GET | `/api/blog/stream/{blog_id}` | SSE stream of agent states |
| GET | `/api/blog/{blog_id}` | Get completed blog |
| GET | `/api/blogs/` | List all blogs (paginated) |
| DELETE | `/api/blog/{blog_id}` | Delete a blog |
| GET | `/api/blog/{blog_id}/logs` | Full agent execution log |
| GET | `/api/health` | Health check |

## Testing

```bash
python -m pytest tests/ -v
```

## Agent Team

| Agent | Role | Tools |
|-------|------|-------|
| Topic Scout | Finds relevant, UPSC-focused topic angles | Tavily search |
| Narrative Planner | Creates blog outline, maps to GS paper | LLM |
| Content Writer | Writes content section-by-section | LLM |
| Fact Checker | Verifies claims via web search | Tavily search |
| Humanizer | Rewrites to bypass AI detection | LLM |
| SEO Optimizer | Scores and improves SEO quality | LLM |
| MCQ Generator | Creates UPSC Prelims-style questions | LLM |
| Image Selector | Finds relevant images | Pexels API |
