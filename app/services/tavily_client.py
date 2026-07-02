from tavily import AsyncTavilyClient

from app.config import settings


class TavilyClient:
    def __init__(self):
        self.client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        response = await self.client.search(query=query, max_results=max_results)
        return response.get("results", [])

    async def get_search_context(self, query: str, max_results: int = 5) -> str:
        results = await self.search(query, max_results)
        context = ""
        for r in results:
            context += f"Source: {r.get('url', '')}\n"
            context += f"Title: {r.get('title', '')}\n"
            context += f"Content: {r.get('content', '')}\n\n"
        return context


tavily_client = TavilyClient()
