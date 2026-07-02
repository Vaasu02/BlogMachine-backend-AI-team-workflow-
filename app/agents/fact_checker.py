import json

from app.agents.base import BaseAgent, AgentResult
from app.services.groq_client import groq_client
from app.services.tavily_client import tavily_client


class FactCheckerAgent(BaseAgent):
    name = "fact_checker"
    description = "Verifies claims in the draft using web search"

    SYSTEM_PROMPT = """You are a rigorous Fact Checker for a UPSC educational blog platform.

Your job is to verify factual claims made in the blog draft. This is critical because UPSC aspirants rely on this content for exam preparation — inaccurate information can harm their preparation.

You must:
1. Identify all factual claims (dates, statistics, names, events, policies, acts)
2. Flag any claim that seems incorrect, outdated, or unverifiable
3. Check for political bias or one-sided narratives
4. Verify that constitutional articles, amendments, and act names are correct
5. Ensure data/statistics cited are from reliable sources

If you find issues, mark verified as false and provide specific feedback about what needs correction.
If everything checks out, mark verified as true.

Respond in JSON format:
{
    "verified": true/false,
    "claims_checked": 10,
    "issues": [
        {
            "claim": "The exact claim that's wrong",
            "section": "Which section it appears in",
            "problem": "What's wrong with it",
            "correction": "What it should say"
        }
    ],
    "suggestions": ["Any general improvement suggestions"],
    "feedback": "If verified is false, a clear message to the writer about what to fix"
}"""

    async def execute(self, input_data: dict) -> AgentResult:
        draft = input_data.get("draft", {})
        topic = input_data.get("topic", "")

        content_text = ""
        sections = draft.get("sections", [])
        for section in sections:
            content_text += f"## {section.get('heading', '')}\n{section.get('content', '')}\n\n"

        try:
            search_results = await tavily_client.search(f"{topic} facts statistics data", max_results=3)
            verification_context = "\n".join(
                f"- {r.get('title', '')}: {r.get('content', '')[:200]}" for r in search_results
            )
        except Exception:
            verification_context = "No web verification available. Use your knowledge to fact-check."

        user_prompt = f"""Blog topic: {topic}

Blog content to fact-check:
{content_text}

Reference information from web search:
{verification_context}

Carefully verify all factual claims. Be strict — UPSC aspirants depend on accuracy. Return JSON only."""

        response = await groq_client.generate(self.SYSTEM_PROMPT, user_prompt)
        output = json.loads(response)

        feedback = output.get("feedback", "")
        verified = output.get("verified", True)

        return AgentResult(
            success=True,
            output=output,
            feedback=feedback if not verified else None,
        )
