import json

from app.agents.base import BaseAgent, AgentResult, parse_json_response
from app.services.gemini_client import gemini_client


class HumanizerAgent(BaseAgent):
    name = "humanizer"
    description = "Rewrites content to sound natural and human-written"

    SYSTEM_PROMPT = """You are a Content Humanizer for a UPSC educational blog platform.

Your job is to rewrite AI-generated content so it reads like a knowledgeable human expert wrote it. Google penalizes AI-generated content dumps, so this step is critical.

Humanization rules:
1. VARY sentence length dramatically — mix 5-word punchy sentences with 25-word flowing ones
2. Add conversational bridges ("Here's where it gets interesting...", "Now, think about this...")
3. Use first person occasionally ("I find this fascinating because...")
4. Add rhetorical questions to engage the reader
5. Break perfect parallel structure — not every list needs to follow the same pattern
6. Include relatable analogies and examples an Indian student would connect with
7. Remove filler words AI loves: "It's important to note", "In conclusion", "Furthermore", "Moreover"
8. Add imperfect transitions — real writers don't always use smooth connectors
9. Include casual asides in parentheses (like this one)
10. Reference the reader directly: "If you're preparing for Prelims..."

DO NOT:
- Change factual content
- Remove important information
- Add fake citations or made-up statistics
- Make it too casual — maintain educational authority

Respond in JSON format:
{
    "title": "Blog title (may refine for SEO/readability)",
    "content": "The full humanized blog content in markdown format (use ## for H2 headings, ### for H3)",
    "changes_made": ["list of key changes you made to humanize the content"]
}"""

    async def execute(self, input_data: dict) -> AgentResult:
        draft = input_data.get("draft", {})
        feedback = input_data.get("feedback")

        content_text = ""
        sections = draft.get("sections", [])
        for section in sections:
            content_text += f"## {section.get('heading', '')}\n{section.get('content', '')}\n\n"

        title = draft.get("title", "")

        feedback_text = ""
        if feedback:
            feedback_text = f"""

REVISION REQUIRED — SEO feedback:
{feedback}

Address the SEO issues while maintaining the human-like tone."""

        user_prompt = f"""Blog title: {title}

Original content:
{content_text}
{feedback_text}

Humanize this content following all the rules. Make it read like a passionate UPSC mentor wrote it, not an AI. Return JSON only."""

        response = await gemini_client.generate(self.SYSTEM_PROMPT, user_prompt)
        output = parse_json_response(response)

        return AgentResult(success=True, output=output)
