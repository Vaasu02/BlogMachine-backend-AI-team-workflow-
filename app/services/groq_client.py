import asyncio
import logging
import time

from groq import AsyncGroq, RateLimitError, APIStatusError

from app.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.total_tokens_used = 0
        self.total_requests = 0
        self._last_request_time = 0.0

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
        max_retries: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        response_format = {"type": "json_object"} if json_mode else None

        for attempt in range(max_retries):
            try:
                now = time.time()
                elapsed = now - self._last_request_time
                if elapsed < 3.0:
                    await asyncio.sleep(3.0 - elapsed)
                self._last_request_time = time.time()

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                self.total_requests += 1
                if response.usage:
                    self.total_tokens_used += response.usage.total_tokens
                    logger.info(
                        f"Groq request #{self.total_requests} — "
                        f"tokens: {response.usage.total_tokens} "
                        f"(prompt: {response.usage.prompt_tokens}, "
                        f"completion: {response.usage.completion_tokens})"
                    )

                return response.choices[0].message.content

            except RateLimitError as e:
                wait_time = 2 ** attempt * 10
                logger.warning(f"Groq rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    raise RuntimeError(f"Groq rate limit exceeded after {max_retries} retries") from e

            except APIStatusError as e:
                if e.status_code >= 500:
                    wait_time = 2 ** attempt * 5
                    logger.warning(f"Groq server error {e.status_code} (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        raise RuntimeError(f"Groq server error after {max_retries} retries: {e.message}") from e
                else:
                    raise RuntimeError(f"Groq API error: {e.status_code} — {e.message}") from e

            except Exception as e:
                logger.error(f"Unexpected Groq error: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    raise

    def get_usage_stats(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_tokens_used": self.total_tokens_used,
        }


groq_client = GroqClient()
