import json

from app.agents.base import BaseAgent, AgentResult, parse_json_response
from app.services.gemini_client import gemini_client


class ContentWriterAgent(BaseAgent):
    name = "content_writer"
    description = "Writes blog content section by section"

    SECTION_PROMPT = """You are a skilled Content Writer for a UPSC educational blog platform.

Your job is to write ONE section of a blog post. You will be given the section heading, its purpose, key points to cover, and context from previous sections.

Writing guidelines:
1. Write in clear, accessible language suitable for UPSC aspirants
2. Use facts, data, and examples — avoid vague generalizations
3. Maintain academic tone but keep it engaging — not boring textbook style
4. Write exactly 200-400 words for this section
5. Use smooth transitions that connect to the previous section's ending
6. Include relevant dates, names, and specific details
7. NO political bias or discrimination
8. Make content relatable to exam preparation without being preachy

IMPORTANT: Write ONLY the section content as plain text. No JSON, no markdown headings, no wrapping. Just the paragraphs for this section."""

    TITLE_PROMPT = """You are a blog title specialist for a UPSC educational platform.

Given the topic and outline, create a compelling blog title.

Rules:
- Under 70 characters
- Includes the primary keyword
- Engaging but not clickbait
- Suitable for UPSC audience

Respond in JSON format:
{
    "title": "The blog title"
}"""

    async def execute(self, input_data: dict) -> AgentResult:
        topic = input_data.get("topic", "")
        narrative = input_data.get("narrative", {})
        research = input_data.get("research", {})
        feedback = input_data.get("feedback")

        outline = narrative.get("outline", [])
        if not outline:
            outline = [{"heading": topic, "purpose": "Main content", "key_points": [], "section_number": 1}]

        keywords = research.get("keywords", [])
        research_context = research.get("context", "")

        title_prompt = f"""Topic: {topic}
Narrative angle: {narrative.get('narrative_angle', '')}
GS Paper: {narrative.get('gs_paper', '')}
Keywords: {', '.join(keywords)}

Generate a blog title. Return JSON only."""

        title_response = await gemini_client.generate(self.TITLE_PROMPT, title_prompt)
        title_data = parse_json_response(title_response)
        title = title_data.get("title", topic)

        sections = []

        for i, section_info in enumerate(outline):
            heading = section_info.get("heading", f"Section {i+1}")
            purpose = section_info.get("purpose", "")
            key_points = section_info.get("key_points", [])

            feedback_text = ""
            if feedback and i == 0:
                feedback_text = f"""
IMPORTANT — REVISION REQUIRED:
The fact checker has flagged issues with the previous draft. Address these:
{feedback}

Fix the flagged issues while keeping the content accurate and well-written."""

            if sections:
                prev_summary = f"(Previous sections: {', '.join(s.get('heading', '') for s in sections)})\n\nLast section ending:\n...{sections[-1].get('content', '')[-200:]}"
            else:
                prev_summary = "(This is the first section)"

            user_prompt = f"""Topic: {topic}
Blog title: {title}
GS Paper: {narrative.get('gs_paper', '')}

Current section ({i+1} of {len(outline)}):
- Heading: {heading}
- Purpose: {purpose}
- Key points to cover: {', '.join(key_points)}

Research context: {research_context[:500]}
Keywords to naturally include: {', '.join(keywords)}

Previous sections:
{prev_summary}
{feedback_text}

Write this section (200-400 words). Connect smoothly to the previous section. Write ONLY the content paragraphs, nothing else."""

            response = await gemini_client.generate(self.SECTION_PROMPT, user_prompt, json_mode=False)
            content = response.strip()
            word_count = len(content.split())

            sections.append({
                "heading": heading,
                "content": content,
                "word_count": word_count,
            })

        total_words = sum(s.get("word_count", 0) for s in sections)

        return AgentResult(
            success=True,
            output={
                "title": title,
                "sections": sections,
                "word_count": total_words,
            },
        )
