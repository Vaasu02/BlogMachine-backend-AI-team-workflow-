import asyncio
import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._last_request_time = 0.0
        self.total_requests = 0
        self.total_tokens_used = 0

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
        max_retries: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 16384,
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        body = {
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        for attempt in range(max_retries):
            try:
                now = time.time()
                elapsed = now - self._last_request_time
                if elapsed < 2.0:
                    await asyncio.sleep(2.0 - elapsed)
                self._last_request_time = time.time()

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json=body)

                if response.status_code == 429:
                    wait_time = 2 ** attempt * 5
                    logger.warning(f"Gemini rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError(f"Gemini rate limit exceeded after {max_retries} retries")

                if response.status_code >= 500:
                    wait_time = 2 ** attempt * 3
                    logger.warning(f"Gemini server error {response.status_code} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError(f"Gemini server error after {max_retries} retries")

                if response.status_code != 200:
                    error_text = response.text[:500]
                    raise RuntimeError(f"Gemini API error {response.status_code}: {error_text}")

                data = response.json()
                self.total_requests += 1

                if "usageMetadata" in data:
                    self.total_tokens_used += data["usageMetadata"].get("totalTokenCount", 0)

                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini returned no candidates")

                finish_reason = candidates[0].get("finishReason", "")
                if finish_reason == "MAX_TOKENS":
                    logger.warning(f"Gemini response was TRUNCATED (hit max_tokens={max_tokens})")

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    raise RuntimeError("Gemini returned empty parts")

                text = parts[0].get("text", "")
                logger.info(f"Gemini request #{self.total_requests} completed (finishReason={finish_reason})")
                return text

            except httpx.TimeoutException:
                logger.warning(f"Gemini timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    raise RuntimeError("Gemini request timed out after all retries")

            except RuntimeError:
                raise

            except Exception as e:
                logger.error(f"Unexpected Gemini error: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(3)
                else:
                    raise

    def get_usage_stats(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_tokens_used": self.total_tokens_used,
        }


gemini_client = GeminiClient()
