import pytest
from unittest.mock import AsyncMock, patch

from app.agents.topic_scout import TopicScoutAgent
from app.agents.narrative import NarrativePlannerAgent
from app.agents.writer import ContentWriterAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.humanizer import HumanizerAgent
from app.agents.seo_optimizer import SEOOptimizerAgent
from app.agents.mcq_generator import MCQGeneratorAgent
from app.agents.image_selector import ImageSelectorAgent


MOCK_TOPIC_SCOUT_RESPONSE = '{"topic": "Indian Economy Post-COVID", "context": "Recovery patterns", "subject": "Economy", "subtopics": ["GDP", "Inflation"], "keywords": ["economy", "recovery"], "sources": []}'

MOCK_NARRATIVE_RESPONSE = '{"gs_paper": "GS3", "subject": "Economy", "narrative_angle": "Recovery story", "outline": [{"section_number": 1, "heading": "Introduction", "purpose": "Set context", "key_points": ["GDP data"], "target_words": 200, "needs_infographic": false}], "upsc_relevance": "GS3 Economy", "intra_links": []}'

MOCK_WRITER_TITLE_RESPONSE = '{"title": "Indian Economy: Post-COVID Recovery Explained"}'
MOCK_WRITER_SECTION_RESPONSE = '{"heading": "Introduction", "content": "India recovery post covid has been remarkable. The GDP growth trajectory shows a V-shaped recovery pattern.", "word_count": 180}'

MOCK_FACT_CHECK_VERIFIED = '{"verified": true, "claims_checked": 5, "issues": [], "suggestions": [], "feedback": ""}'
MOCK_FACT_CHECK_REJECTED = '{"verified": false, "claims_checked": 5, "issues": [{"claim": "GDP grew 9%", "section": "Introduction", "problem": "Incorrect figure", "correction": "GDP grew 7.2%"}], "suggestions": [], "feedback": "Fix GDP figure in introduction"}'

MOCK_HUMANIZER_RESPONSE = '{"title": "Indian Economy: Post-COVID Recovery Explained", "content": "## Introduction\\nHere is the thing about India recovery...", "changes_made": ["Added conversational tone"]}'

MOCK_SEO_HIGH = '{"seo_score": 78, "meta_description": "Explore India post-COVID recovery", "tags": ["economy", "UPSC"], "scores": {}, "improvements": [], "feedback": ""}'
MOCK_SEO_LOW = '{"seo_score": 55, "meta_description": "test", "tags": ["economy"], "scores": {}, "improvements": ["Add more keywords"], "feedback": "Keyword density too low"}'

MOCK_MCQ_RESPONSE = '{"questions": [{"id": 1, "question": "What was India GDP growth?", "options": ["A) 5%", "B) 7.2%", "C) 9%", "D) 3%"], "correct_answer": "B", "explanation": "India GDP grew 7.2%", "difficulty": "moderate"}]}'


@pytest.mark.asyncio
class TestTopicScoutAgent:
    @patch("app.agents.topic_scout.groq_client.generate", new_callable=AsyncMock)
    @patch("app.agents.topic_scout.tavily_client.search", new_callable=AsyncMock)
    async def test_success(self, mock_search, mock_generate):
        mock_search.return_value = [{"title": "Test", "content": "Content", "url": "http://test.com"}]
        mock_generate.return_value = MOCK_TOPIC_SCOUT_RESPONSE

        agent = TopicScoutAgent()
        result = await agent.execute({"topic": "Indian Economy"})

        assert result.success is True
        assert result.output["topic"] == "Indian Economy Post-COVID"
        assert result.output["subject"] == "Economy"
        assert len(result.output["sources"]) == 1

    @patch("app.agents.topic_scout.groq_client.generate", new_callable=AsyncMock)
    @patch("app.agents.topic_scout.tavily_client.search", new_callable=AsyncMock)
    async def test_tavily_failure_still_works(self, mock_search, mock_generate):
        mock_search.side_effect = Exception("API down")
        mock_generate.return_value = MOCK_TOPIC_SCOUT_RESPONSE

        agent = TopicScoutAgent()
        result = await agent.execute({"topic": "Indian Economy"})

        assert result.success is True


@pytest.mark.asyncio
class TestNarrativePlannerAgent:
    @patch("app.agents.narrative.groq_client.generate", new_callable=AsyncMock)
    async def test_success(self, mock_generate):
        mock_generate.return_value = MOCK_NARRATIVE_RESPONSE

        agent = NarrativePlannerAgent()
        result = await agent.execute({"topic": "Indian Economy", "research": {"context": "test"}})

        assert result.success is True
        assert result.output["gs_paper"] == "GS3"
        assert len(result.output["outline"]) == 1


@pytest.mark.asyncio
class TestContentWriterAgent:
    @patch("app.agents.writer.groq_client.generate", new_callable=AsyncMock)
    async def test_section_by_section_writing(self, mock_generate):
        mock_generate.side_effect = [MOCK_WRITER_TITLE_RESPONSE, MOCK_WRITER_SECTION_RESPONSE]

        agent = ContentWriterAgent()
        result = await agent.execute({
            "topic": "Indian Economy",
            "narrative": {"outline": [{"heading": "Intro", "purpose": "Set context", "key_points": ["GDP"], "section_number": 1}], "gs_paper": "GS3", "narrative_angle": "Recovery"},
            "research": {"context": "test", "keywords": ["economy"]},
            "feedback": None,
        })

        assert result.success is True
        assert result.output["title"] == "Indian Economy: Post-COVID Recovery Explained"
        assert len(result.output["sections"]) == 1
        assert mock_generate.call_count == 2  # 1 title + 1 section


@pytest.mark.asyncio
class TestFactCheckerAgent:
    @patch("app.agents.fact_checker.groq_client.generate", new_callable=AsyncMock)
    @patch("app.agents.fact_checker.tavily_client.search", new_callable=AsyncMock)
    async def test_verified_pass(self, mock_search, mock_generate):
        mock_search.return_value = []
        mock_generate.return_value = MOCK_FACT_CHECK_VERIFIED

        agent = FactCheckerAgent()
        result = await agent.execute({"draft": {"sections": [{"heading": "Test", "content": "Content"}]}, "topic": "Test"})

        assert result.success is True
        assert result.output["verified"] is True
        assert result.feedback is None

    @patch("app.agents.fact_checker.groq_client.generate", new_callable=AsyncMock)
    @patch("app.agents.fact_checker.tavily_client.search", new_callable=AsyncMock)
    async def test_verified_rejected(self, mock_search, mock_generate):
        mock_search.return_value = []
        mock_generate.return_value = MOCK_FACT_CHECK_REJECTED

        agent = FactCheckerAgent()
        result = await agent.execute({"draft": {"sections": [{"heading": "Test", "content": "GDP grew 9%"}]}, "topic": "Test"})

        assert result.success is True
        assert result.output["verified"] is False
        assert result.feedback == "Fix GDP figure in introduction"


@pytest.mark.asyncio
class TestHumanizerAgent:
    @patch("app.agents.humanizer.groq_client.generate", new_callable=AsyncMock)
    async def test_success(self, mock_generate):
        mock_generate.return_value = MOCK_HUMANIZER_RESPONSE

        agent = HumanizerAgent()
        result = await agent.execute({"draft": {"sections": [{"heading": "Test", "content": "Content"}], "title": "Test Title"}, "feedback": None})

        assert result.success is True
        assert "content" in result.output
        assert "changes_made" in result.output


@pytest.mark.asyncio
class TestSEOOptimizerAgent:
    @patch("app.agents.seo_optimizer.groq_client.generate", new_callable=AsyncMock)
    async def test_high_score_no_feedback(self, mock_generate):
        mock_generate.return_value = MOCK_SEO_HIGH

        agent = SEOOptimizerAgent()
        result = await agent.execute({"content": {"content": "blog text", "title": "Test"}, "topic": "Test"})

        assert result.success is True
        assert result.output["seo_score"] == 78
        assert result.feedback is None

    @patch("app.agents.seo_optimizer.groq_client.generate", new_callable=AsyncMock)
    async def test_low_score_returns_feedback(self, mock_generate):
        mock_generate.return_value = MOCK_SEO_LOW

        agent = SEOOptimizerAgent()
        result = await agent.execute({"content": {"content": "blog text", "title": "Test"}, "topic": "Test"})

        assert result.success is True
        assert result.output["seo_score"] == 55
        assert result.feedback == "Keyword density too low"


@pytest.mark.asyncio
class TestMCQGeneratorAgent:
    @patch("app.agents.mcq_generator.groq_client.generate", new_callable=AsyncMock)
    async def test_success(self, mock_generate):
        mock_generate.return_value = MOCK_MCQ_RESPONSE

        agent = MCQGeneratorAgent()
        result = await agent.execute({"content": {"content": "blog text"}, "topic": "Indian Economy"})

        assert result.success is True
        assert len(result.output["questions"]) == 1
        assert result.output["questions"][0]["correct_answer"] == "B"


@pytest.mark.asyncio
class TestImageSelectorAgent:
    @patch("app.agents.image_selector.pexels_client.search_photos", new_callable=AsyncMock)
    async def test_success(self, mock_search):
        mock_search.return_value = [
            {"url": "http://img1.jpg", "alt_text": "economy", "credit": "John"},
            {"url": "http://img2.jpg", "alt_text": "india", "credit": "Jane"},
        ]

        agent = ImageSelectorAgent()
        result = await agent.execute({"topic": "Indian Economy", "title": "Test Title"})

        assert result.success is True
        assert len(result.output["images"]) == 2
        assert result.output["images"][0]["placement"] == "banner"

    @patch("app.agents.image_selector.pexels_client.search_photos", new_callable=AsyncMock)
    async def test_api_failure_returns_empty(self, mock_search):
        mock_search.side_effect = Exception("API down")

        agent = ImageSelectorAgent()
        result = await agent.execute({"topic": "Indian Economy", "title": "Test"})

        assert result.success is True
        assert result.output["images"] == []


@pytest.mark.asyncio
class TestGroqRateLimitHandling:
    @patch("app.agents.topic_scout.tavily_client.search", new_callable=AsyncMock)
    @patch("app.agents.topic_scout.groq_client.generate", new_callable=AsyncMock)
    async def test_groq_exception_propagates(self, mock_generate, mock_search):
        mock_search.return_value = []
        mock_generate.side_effect = RuntimeError("Groq rate limit exceeded after 3 retries")

        agent = TopicScoutAgent()
        with pytest.raises(RuntimeError, match="rate limit"):
            await agent.execute({"topic": "Test"})


@pytest.mark.asyncio
class TestInvalidJSONHandling:
    @patch("app.agents.topic_scout.tavily_client.search", new_callable=AsyncMock)
    @patch("app.agents.topic_scout.groq_client.generate", new_callable=AsyncMock)
    async def test_invalid_json_raises_error(self, mock_generate, mock_search):
        mock_search.return_value = []
        mock_generate.return_value = "This is not valid JSON at all"

        agent = TopicScoutAgent()
        with pytest.raises(Exception):
            await agent.execute({"topic": "Test"})

    @patch("app.agents.narrative.groq_client.generate", new_callable=AsyncMock)
    async def test_narrative_invalid_json_raises(self, mock_generate):
        mock_generate.return_value = "```json\n{broken json"

        agent = NarrativePlannerAgent()
        with pytest.raises(Exception):
            await agent.execute({"topic": "Test", "research": {}})

    @patch("app.agents.mcq_generator.groq_client.generate", new_callable=AsyncMock)
    async def test_mcq_invalid_json_raises(self, mock_generate):
        mock_generate.return_value = "{incomplete"

        agent = MCQGeneratorAgent()
        with pytest.raises(Exception):
            await agent.execute({"content": {"content": "text"}, "topic": "Test"})
