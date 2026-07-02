import json

from app.agents.base import BaseAgent, AgentResult
from app.services.groq_client import groq_client


class SEOOptimizerAgent(BaseAgent):
    name = "seo_optimizer"
    description = "Evaluates and improves SEO quality of the blog"

    SYSTEM_PROMPT = """You are an SEO Specialist for a UPSC educational blog platform.

Your job is to evaluate the blog content for SEO quality and provide a score.

Evaluation criteria (score each 1-10):
1. Title — Under 60 chars, includes primary keyword, compelling?
2. Meta description — Would it work as a 150-160 char Google snippet?
3. Heading structure — Proper H2/H3 hierarchy? Descriptive headings?
4. Keyword usage — Primary keyword appears naturally 3-5 times?
5. Readability — Short paragraphs? Mix of sentence lengths? Scannable?
6. Content length — Substantial enough (800+ words)?

Score each criterion 1-10, average them, and scale to 100.

IMPORTANT:
- Do NOT penalize for lack of internal links — this is a standalone blog post.
- Do NOT penalize for missing images or multimedia — those are handled separately.
- Score ONLY what the content itself can control.
- Be fair and varied — not every blog is the same quality. Scores should range from 60-95.
- Only provide feedback if score < 65.

Respond in JSON format:
{
    "seo_score": 78,
    "meta_description": "A compelling 150-160 character description for Google",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "scores": {
        "title": 8,
        "meta_description": 7,
        "heading_structure": 8,
        "keyword_usage": 7,
        "readability": 8,
        "content_length": 7
    },
    "improvements": ["specific improvement 1", "specific improvement 2"],
    "feedback": "Only if score < 65: what the humanizer should fix"
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
            feedback=feedback if seo_score < 65 else None,
        )
