import json

from app.agents.base import BaseAgent, AgentResult
from app.services.groq_client import groq_client


class NarrativePlannerAgent(BaseAgent):
    name = "narrative_planner"
    description = "Creates blog structure and UPSC narrative angle"

    SYSTEM_PROMPT = """You are a Content Strategist specializing in UPSC exam preparation content.

Your job is to create a detailed blog outline with a strong narrative that connects to UPSC Mains examination.

You must:
1. Map the topic to the relevant GS paper (GS1: History/Geography/Society, GS2: Polity/Governance/IR, GS3: Economy/Science/Environment, GS4: Ethics)
2. Create a section-by-section outline (3-4 sections only)
3. Define the narrative arc — how sections flow logically
4. Plan a callout section connecting to UPSC Mains relevance

Each section should have a clear purpose and roughly 200-400 words target.

Respond in JSON format:
{
    "gs_paper": "GS1/GS2/GS3/GS4",
    "subject": "Subject area like Economy, Polity etc",
    "narrative_angle": "One sentence describing the storytelling approach",
    "outline": [
        {
            "section_number": 1,
            "heading": "Section title",
            "purpose": "What this section achieves",
            "key_points": ["point1", "point2"],
            "target_words": 200,
            "needs_infographic": false
        }
    ],
    "upsc_relevance": "How this connects to UPSC Mains — which paper, which topic area",
    "intra_links": ["section X references section Y concept"]
}"""

    async def execute(self, input_data: dict) -> AgentResult:
        topic = input_data.get("topic", "")
        research = input_data.get("research", {})

        research_context = ""
        if research:
            research_context = f"""
Research context: {research.get('context', '')}
Subject: {research.get('subject', '')}
Subtopics to cover: {', '.join(research.get('subtopics', []))}
Keywords: {', '.join(research.get('keywords', []))}"""

        user_prompt = f"""Topic: {topic}
{research_context}

Create a detailed blog outline for UPSC aspirants. The blog should be educational, engaging, and structured for exam preparation. Return JSON only."""

        response = await groq_client.generate(self.SYSTEM_PROMPT, user_prompt)
        output = json.loads(response)

        return AgentResult(success=True, output=output)
