import json

from app.agents.base import BaseAgent, AgentResult
from app.services.groq_client import groq_client
from app.services.tavily_client import tavily_client


class TopicScoutAgent(BaseAgent):
    name = "topic_scout"
    description = "Searches for trending topics and validates against history"

    SYSTEM_PROMPT = """You are a Topic Research Specialist for a UPSC-focused educational blog platform.

Your job is to analyze the given topic and find relevant, timely angles that would interest UPSC aspirants.

You must:
1. Identify the core subject area (History, Geography, Polity, Economy, Science, Environment, Ethics, Current Affairs)
2. Find a specific, focused angle that is both timely and exam-relevant
3. Suggest 3-5 related subtopics that should be covered
4. Identify keywords that UPSC aspirants would search for

Respond in JSON format:
{
    "topic": "The refined/focused topic title",
    "context": "A 2-3 sentence summary of why this topic is relevant for UPSC aspirants right now",
    "subject": "The UPSC subject area (e.g., Geography, Polity, Economy)",
    "subtopics": ["subtopic1", "subtopic2", "subtopic3"],
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "sources": []
}"""

    async def execute(self, input_data: dict) -> AgentResult:
        topic = input_data.get("topic", "")
        search_query = f"UPSC {topic} current affairs 2024 2025"

        try:
            search_results = await tavily_client.search(search_query, max_results=5)
            search_context = "\n".join(
                f"- {r.get('title', '')}: {r.get('content', '')[:200]}" for r in search_results
            )
            sources = [{"url": r.get("url", ""), "title": r.get("title", "")} for r in search_results]
        except Exception:
            search_context = ""
            sources = []

        user_prompt = f"""Topic: {topic}

Web research context:
{search_context if search_context else "No web results available. Use your knowledge."}

Analyze this topic and provide a focused, UPSC-relevant angle. Return JSON only."""

        response = await groq_client.generate(self.SYSTEM_PROMPT, user_prompt)
        output = json.loads(response)
        output["sources"] = sources
        output["search_queries"] = [search_query]

        return AgentResult(success=True, output=output)
