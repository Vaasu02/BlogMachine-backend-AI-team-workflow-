from app.agents.base import BaseAgent, AgentResult
from app.services.pexels_client import pexels_client


class ImageSelectorAgent(BaseAgent):
    name = "image_selector"
    description = "Finds relevant images for the blog from Pexels"

    async def execute(self, input_data: dict) -> AgentResult:
        topic = input_data.get("topic", "")
        title = input_data.get("title", topic)

        try:
            images = await pexels_client.search_photos(query=title, count=3)

            if not images:
                images = await pexels_client.search_photos(query=topic, count=3)

            output = {
                "images": [
                    {
                        "url": img["url"],
                        "alt_text": img["alt_text"],
                        "credit": img["credit"],
                        "placement": "banner" if i == 0 else f"section_{i}",
                    }
                    for i, img in enumerate(images)
                ]
            }
        except Exception:
            output = {"images": []}

        return AgentResult(success=True, output=output)
