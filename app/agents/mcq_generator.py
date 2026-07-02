import json

from app.agents.base import BaseAgent, AgentResult
from app.services.groq_client import groq_client


class MCQGeneratorAgent(BaseAgent):
    name = "mcq_generator"
    description = "Generates UPSC-style MCQs based on blog content"

    SYSTEM_PROMPT = """You are an MCQ Specialist creating UPSC Prelims-style questions.

Your job is to generate 5 high-quality multiple-choice questions based on the blog content. These should test conceptual understanding, not rote memorization.

MCQ Guidelines (UPSC Prelims style):
1. Questions should test application and analysis, not just recall
2. Options should be plausible — no obviously wrong answers
3. Include "Which of the following statements is/are correct?" style questions
4. Include at least one question with "1 and 2 only", "2 and 3 only" type options
5. Explanations should reference why each wrong option is wrong
6. Difficulty level: moderate to hard (Prelims standard)
7. Questions must be factually grounded in the blog content

Respond in JSON format:
{
    "questions": [
        {
            "id": 1,
            "question": "The question text",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "correct_answer": "B",
            "explanation": "Why B is correct and why others are wrong",
            "difficulty": "moderate/hard"
        }
    ]
}"""

    async def execute(self, input_data: dict) -> AgentResult:
        content = input_data.get("content", {})
        topic = input_data.get("topic", "")

        blog_content = content.get("content", "")

        user_prompt = f"""Topic: {topic}

Blog content:
{blog_content}

Generate 5 UPSC Prelims-style MCQs based on this content. Questions should test deep understanding. Return JSON only."""

        response = await groq_client.generate(self.SYSTEM_PROMPT, user_prompt)
        output = json.loads(response)

        return AgentResult(success=True, output=output)
