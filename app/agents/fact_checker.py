import json

from app.agents.base import BaseAgent, AgentResult, parse_json_response
from app.services.gemini_client import gemini_client
from app.services.tavily_client import tavily_client


class FactCheckerAgent(BaseAgent):
    name = "fact_checker"
    description = "Verifies claims in the draft using web search"

    SYSTEM_PROMPT = """You are a Fact Checker for a UPSC educational blog platform.

Your job is to verify factual claims made in the blog draft. UPSC aspirants rely on this content, so accuracy matters.

PROCESS:
1. Read through the content and IDENTIFY every factual claim (dates, names, statistics, events, legal provisions).
2. Cross-reference against the provided web search results and your knowledge.
3. Count how many claims you checked (must be at least 8).
4. Only mark verified=false if you find a SPECIFIC error with a CONCRETE correction.

Rules:
1. You MUST check at least 8-15 claims from the content. Count them.
2. Only flag claims that are DEMONSTRABLY WRONG — you must state what the correct fact is.
3. Do NOT flag claims just because you cannot verify them. Unverifiable is NOT the same as wrong.
4. Do NOT give generic feedback like "verify sources" or "ensure accuracy."
5. If you cannot find a specific factual error with a concrete correction, mark verified as TRUE.

Respond in JSON format:
{
    "verified": true/false,
    "claims_checked": 12,
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

        search_query = f"{topic} facts statistics data"
        sources_used = []
        try:
            search_results = await tavily_client.search(search_query, max_results=3)
            verification_context = "\n".join(
                f"- {r.get('title', '')}: {r.get('content', '')[:200]}" for r in search_results
            )
            sources_used = [{"url": r.get("url", ""), "title": r.get("title", "")} for r in search_results]
        except Exception:
            verification_context = "No web verification available. Use your knowledge to fact-check."

        user_prompt = f"""Blog topic: {topic}

Blog content to fact-check:
{content_text}

Reference information from web search:
{verification_context}

Carefully verify all factual claims. Only flag claims that are DEMONSTRABLY WRONG with a concrete correction. Return JSON only."""

        response = await gemini_client.generate(self.SYSTEM_PROMPT, user_prompt)
        output = parse_json_response(response)
        output["sources_used"] = sources_used
        output["search_query"] = search_query

        feedback = output.get("feedback", "")
        verified = output.get("verified", True)

        return AgentResult(
            success=True,
            output=output,
            feedback=feedback if not verified else None,
        )
