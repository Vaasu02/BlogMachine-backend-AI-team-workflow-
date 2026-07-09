from app.agents.base import BaseAgent, AgentResult
from app.services.gemini_client import gemini_client


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

OUTPUT FORMAT (one item per line, exact format):
SEO_SCORE: [number]
TITLE_SCORE: [number]
META_SCORE: [number]
HEADING_SCORE: [number]
KEYWORD_SCORE: [number]
READABILITY_SCORE: [number]
LENGTH_SCORE: [number]
META_DESCRIPTION: [your 150-160 char description]
TAGS: [tag1, tag2, tag3, tag4, tag5]
IMPROVEMENTS: [improvement 1 | improvement 2 | improvement 3]
FEEDBACK: [only if score < 65, otherwise write NONE]"""

    async def execute(self, input_data: dict) -> AgentResult:
        content = input_data.get("content", {})
        topic = input_data.get("topic", "")

        blog_content = content.get("content", "")
        title = content.get("title", "")

        user_prompt = f"""Topic: {topic}
Blog title: {title}

Blog content:
{blog_content}

Evaluate the SEO quality of this blog. Be strict but fair. Score it and provide actionable feedback."""

        response = await gemini_client.generate(self.SYSTEM_PROMPT, user_prompt, json_mode=False)
        output = self._parse_seo_response(response)

        seo_score = output.get("seo_score", 0)
        feedback = output.get("feedback", "")

        return AgentResult(
            success=True,
            output=output,
            feedback=feedback if seo_score < 65 else None,
        )

    def _parse_seo_response(self, text: str) -> dict:
        """Parse the structured plain text SEO response."""
        lines = text.strip().split("\n")
        result = {
            "seo_score": 70,
            "scores": {},
            "meta_description": "",
            "tags": [],
            "improvements": [],
            "feedback": "",
        }

        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().upper()
            value = value.strip()

            try:
                if key == "SEO_SCORE":
                    result["seo_score"] = int(value)
                elif key == "TITLE_SCORE":
                    result["scores"]["title"] = int(value)
                elif key == "META_SCORE":
                    result["scores"]["meta_description"] = int(value)
                elif key == "HEADING_SCORE":
                    result["scores"]["heading_structure"] = int(value)
                elif key == "KEYWORD_SCORE":
                    result["scores"]["keyword_usage"] = int(value)
                elif key == "READABILITY_SCORE":
                    result["scores"]["readability"] = int(value)
                elif key == "LENGTH_SCORE":
                    result["scores"]["content_length"] = int(value)
                elif key == "META_DESCRIPTION":
                    result["meta_description"] = value
                elif key == "TAGS":
                    result["tags"] = [t.strip() for t in value.strip("[]").split(",")]
                elif key == "IMPROVEMENTS":
                    result["improvements"] = [i.strip() for i in value.strip("[]").split("|")]
                elif key == "FEEDBACK":
                    result["feedback"] = "" if value.upper() == "NONE" else value
            except (ValueError, IndexError):
                continue

        return result
