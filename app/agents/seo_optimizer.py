import json

from app.agents.base import BaseAgent, AgentResult
from app.services.groq_client import groq_client


class SEOOptimizerAgent(BaseAgent):
    name = "seo_optimizer"
    description = "Evaluates and improves SEO quality of the blog"

    SYSTEM_PROMPT = """You are an SEO Specialist for a UPSC educational blog platform.

Your job is to evaluate the blog content for SEO quality and provide a score. If the score is below 70, provide specific feedback on what needs improvement.

Evaluation criteria:
1. Title — Is it under 60 chars, includes primary keyword, compelling?
2. Meta description — Would it work as a 150-160 char Google snippet?
3. Heading structure — Proper H2/H3 hierarchy? Descriptive headings with keywords?
4. Keyword density — Primary keyword appears 3-5 times naturally? Related keywords present?
5. Readability — Short paragraphs? Mix of sentence lengths? Scannable?
6. Internal linking potential — Are there sections that reference each other (intra-links)?
7. Content length — Is it substantial enough (1200+ words)?
8. Engagement hooks — Does it have questions, callouts, or interactive elements?

Score each criterion 1-10, then average for overall score (scale to 100).

Respond in JSON format:
{
    "seo_score": 75,
    "meta_description": "A compelling 150-160 character description for Google",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "scores": {
        "title": 8,
        "meta_description": 7,
        "heading_structure": 8,
        "keyword_density": 6,
        "readability": 8,
        "intra_linking": 5,
        "content_length": 7,
        "engagement": 7
    },
    "improvements": ["specific improvement 1", "specific improvement 2"],
    "feedback": "If score < 70, detailed feedback for the humanizer about what to fix"
}"""

    async def execute(self, input_data: dict) -> AgentResult:
        content = input_data.get("content", {})
        topic = input_data.get("topic", "")

        blog_content = content.get("content", "")
        title = content.get("title", "")

        user_prompt = f"""Topic: {topic}
Blog title: {title}

Blog content:
{blog_content}

Evaluate the SEO quality of this blog. Be strict but fair. Score it and provide actionable feedback. Return JSON only."""

        response = await groq_client.generate(self.SYSTEM_PROMPT, user_prompt)
        output = json.loads(response)

        seo_score = output.get("seo_score", 0)
        feedback = output.get("feedback", "")

        return AgentResult(
            success=True,
            output=output,
            feedback=feedback if seo_score < 70 else None,
        )
