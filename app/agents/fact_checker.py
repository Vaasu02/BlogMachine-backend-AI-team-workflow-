import json

from app.agents.base import BaseAgent, AgentResult
from app.services.groq_client import groq_client
from app.services.tavily_client import tavily_client


class FactCheckerAgent(BaseAgent):
    name = "fact_checker"
    description = "Verifies claims in the draft using web search"

    SYSTEM_PROMPT = """You are a Fact Checker for a UPSC educational blog platform.

Your job is to verify factual claims made in the blog draft. UPSC aspirants rely on this content, so accuracy matters.

Rules:
1. Only flag claims that are DEMONSTRABLY WRONG — you must state what the correct fact is.
2. Do NOT flag claims just because you cannot verify them. Unverifiable is NOT the same as wrong.
3. Do NOT give generic feedback like "verify sources" or "ensure accuracy" — that is useless.
4. If you cannot find a specific factual error with a concrete correction, mark verified as TRUE.
5. Vague concerns ("dates need checking", "statistics should be verified") do NOT count as issues.

Only mark verified=false if you have at least ONE specific claim with a concrete correction.

Respond in JSON format:
{
    "verified": true/false,
    "claims_checked": 10,
    "issues": [
        {
            "claim": "The exact incorrect claim",
            "problem": "What is specifically wrong",
            "correction": "The correct information with source"
        }
    ],
    "feedback": "ONLY if verified=false: Tell the writer EXACTLY which facts to change and what to change them to"
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
