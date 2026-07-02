import httpx

from app.config import settings


class PexelsClient:
    BASE_URL = "https://api.pexels.com/v1"

    def __init__(self):
        self.api_key = settings.PEXELS_API_KEY

    async def search_photos(self, query: str, count: int = 3) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/search",
                params={"query": query, "per_page": count},
                headers={"Authorization": self.api_key},
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results = []
            for photo in data.get("photos", []):
                results.append({
                    "url": photo["src"]["large"],
                    "alt_text": photo.get("alt", query),
                    "credit": photo["photographer"],
                })
            return results


pexels_client = PexelsClient()
