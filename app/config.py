import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./blog_machine.db")
    GEMINI_MODEL: str = "gemini-2.0-flash-lite"
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    MAX_FEEDBACK_RETRIES: int = 3


settings = Settings()
