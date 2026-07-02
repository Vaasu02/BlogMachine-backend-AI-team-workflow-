import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.orchestrator.state_machine import (
    PipelineContext,
    get_next_state,
    run_blog_pipeline,
    emit_event,
)
from app.orchestrator.states import BlogState
from app.orchestrator.event_bus import event_bus
from app.agents.base import AgentResult


class TestPipelineContext:
    def test_initial_state(self):
        ctx = PipelineContext("blog-123", "Indian Economy")
        assert ctx.blog_id == "blog-123"
        assert ctx.topic == "Indian Economy"
        assert ctx.research == {}
        assert ctx.draft == {}

    def test_get_input_for_topic_research(self):
        ctx = PipelineContext("blog-123", "Indian Economy")
        input_data = ctx.get_input_for_state(BlogState.TOPIC_RESEARCH)
        assert input_data == {"topic": "Indian Economy"}

    def test_get_input_for_writing_includes_feedback(self):
        ctx = PipelineContext("blog-123", "Indian Economy")
        ctx.research = {"context": "test context", "keywords": ["gdp"]}
        ctx.narrative = {"outline": [], "gs_paper": "GS3"}
        ctx.fact_check = {"feedback": "Fix the GDP figure"}
        input_data = ctx.get_input_for_state(BlogState.WRITING)
        assert input_data["feedback"] == "Fix the GDP figure"

    def test_store_output(self):
        ctx = PipelineContext("blog-123", "Indian Economy")
        ctx.store_output(BlogState.TOPIC_RESEARCH, {"topic": "test", "context": "ctx"})
        assert ctx.research == {"topic": "test", "context": "ctx"}

    def test_store_and_retrieve_all_states(self):
        ctx = PipelineContext("blog-123", "Test")
        ctx.store_output(BlogState.TOPIC_RESEARCH, {"data": "research"})
        ctx.store_output(BlogState.NARRATIVE_PLANNING, {"data": "narrative"})
        ctx.store_output(BlogState.WRITING, {"data": "draft"})
        ctx.store_output(BlogState.FACT_CHECKING, {"data": "fact_check"})
        ctx.store_output(BlogState.HUMANIZING, {"data": "humanized"})
        ctx.store_output(BlogState.SEO_CHECK, {"data": "seo"})
        ctx.store_output(BlogState.MCQ_GENERATION, {"data": "mcqs"})
        ctx.store_output(BlogState.IMAGE_SELECTION, {"data": "images"})

        assert ctx.research == {"data": "research"}
        assert ctx.narrative == {"data": "narrative"}
        assert ctx.draft == {"data": "draft"}
        assert ctx.fact_check == {"data": "fact_check"}
        assert ctx.humanized == {"data": "humanized"}
        assert ctx.seo == {"data": "seo"}
        assert ctx.mcqs == {"data": "mcqs"}
        assert ctx.images == {"data": "images"}


class TestGetNextState:
    def test_fact_check_verified_goes_to_humanizing(self):
        result = AgentResult(success=True, output={"verified": True})
        next_state = get_next_state(BlogState.FACT_CHECKING, result)
        assert next_state == BlogState.HUMANIZING

    def test_fact_check_rejected_goes_to_writing(self):
        result = AgentResult(success=True, output={"verified": False}, feedback="Fix paragraph 2")
        next_state = get_next_state(BlogState.FACT_CHECKING, result)
        assert next_state == BlogState.WRITING

    def test_seo_high_score_goes_to_mcq(self):
        result = AgentResult(success=True, output={"seo_score": 75})
        next_state = get_next_state(BlogState.SEO_CHECK, result)
        assert next_state == BlogState.MCQ_GENERATION

    def test_seo_low_score_goes_to_humanizer(self):
        result = AgentResult(success=True, output={"seo_score": 55})
        next_state = get_next_state(BlogState.SEO_CHECK, result)
        assert next_state == BlogState.HUMANIZING

    def test_failed_result_goes_to_failed(self):
        result = AgentResult(success=False, output={})
        next_state = get_next_state(BlogState.WRITING, result)
        assert next_state == BlogState.FAILED

    def test_topic_research_success_goes_to_narrative(self):
        result = AgentResult(success=True, output={"topic": "test"})
        next_state = get_next_state(BlogState.TOPIC_RESEARCH, result)
        assert next_state == BlogState.NARRATIVE_PLANNING

    def test_humanizing_success_goes_to_seo(self):
        result = AgentResult(success=True, output={"content": "text"})
        next_state = get_next_state(BlogState.HUMANIZING, result)
        assert next_state == BlogState.SEO_CHECK

    def test_image_selection_success_goes_to_completed(self):
        result = AgentResult(success=True, output={"images": []})
        next_state = get_next_state(BlogState.IMAGE_SELECTION, result)
        assert next_state == BlogState.COMPLETED


@pytest.mark.asyncio
class TestFeedbackRetryLimits:
    @patch("app.orchestrator.state_machine.get_agent_instance")
    @patch("app.orchestrator.state_machine.SessionLocal")
    async def test_fact_check_max_retries_forces_proceed(self, mock_session_cls, mock_get_agent):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.query.return_value.filter.return_value.update = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

        call_count = {"topic": 0, "narrative": 0, "writer": 0, "fact_checker": 0, "humanizer": 0, "seo": 0, "mcq": 0, "image": 0}

        async def mock_agent_execute(input_data):
            agent_name = mock_get_agent.return_value.name
            if agent_name == "fact_checker":
                call_count["fact_checker"] += 1
                return AgentResult(success=True, output={"verified": False}, feedback="Bad data")
            return AgentResult(success=True, output={
                "topic": "test", "context": "", "sources": [],
                "outline": [], "gs_paper": "GS3", "narrative_angle": "", "subject": "Economy",
                "sections": [], "word_count": 0, "title": "Test",
                "content": "text", "changes_made": [],
                "seo_score": 80, "meta_description": "", "tags": [], "improvements": [],
                "questions": [],
                "images": [],
                "verified": True,
            })

        agent_sequence = iter([
            "topic_scout", "narrative_planner", "content_writer", "fact_checker",
            "content_writer", "fact_checker",
            "content_writer", "fact_checker",
            "content_writer", "fact_checker",  # 4th time — should be forced through
            "humanizer", "seo_optimizer", "mcq_generator", "image_selector",
        ])

        def create_mock_agent(state):
            mock_agent = AsyncMock()
            try:
                name = next(agent_sequence)
            except StopIteration:
                name = "unknown"
            mock_agent.name = name
            mock_agent.execute = mock_agent_execute
            mock_get_agent.return_value = mock_agent
            return mock_agent

        mock_get_agent.side_effect = create_mock_agent

        await run_blog_pipeline("test-blog-id", "Test Topic")

        # Fact checker called max 4 times (initial + 3 retries), then forced through
        assert call_count["fact_checker"] <= 4

    @patch("app.orchestrator.state_machine.get_agent_instance")
    @patch("app.orchestrator.state_machine.SessionLocal")
    async def test_seo_max_retries_forces_proceed(self, mock_session_cls, mock_get_agent):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.query.return_value.filter.return_value.update = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

        seo_call_count = 0

        async def mock_agent_execute(input_data):
            nonlocal seo_call_count
            agent_name = mock_get_agent.return_value.name
            if agent_name == "seo_optimizer":
                seo_call_count += 1
                return AgentResult(success=True, output={"seo_score": 40, "meta_description": "", "tags": [], "improvements": []}, feedback="Score too low")
            return AgentResult(success=True, output={
                "topic": "test", "context": "", "sources": [],
                "outline": [], "gs_paper": "GS3", "narrative_angle": "", "subject": "Economy",
                "sections": [], "word_count": 0, "title": "Test",
                "verified": True, "issues": [], "suggestions": [],
                "content": "text", "changes_made": [],
                "questions": [],
                "images": [],
            })

        agent_names = iter([
            "topic_scout", "narrative_planner", "content_writer", "fact_checker",
            "humanizer", "seo_optimizer",
            "humanizer", "seo_optimizer",
            "humanizer", "seo_optimizer",
            "humanizer", "seo_optimizer",  # 4th SEO — forced through
            "mcq_generator", "image_selector",
        ])

        def create_mock_agent(state):
            mock_agent = AsyncMock()
            try:
                name = next(agent_names)
            except StopIteration:
                name = "unknown"
            mock_agent.name = name
            mock_agent.execute = mock_agent_execute
            mock_get_agent.return_value = mock_agent
            return mock_agent

        mock_get_agent.side_effect = create_mock_agent

        await run_blog_pipeline("test-blog-id", "Test Topic")

        assert seo_call_count <= 4


@pytest.mark.asyncio
class TestEventBus:
    async def test_subscribe_and_publish(self):
        queue = event_bus.subscribe("test-blog")
        await event_bus.publish("test-blog", {"state": "running", "agent": "writer"})

        event = await asyncio.wait_for(queue.get(), timeout=1)
        assert event["state"] == "running"
        assert event["agent"] == "writer"

        event_bus.unsubscribe("test-blog", queue)

    async def test_multiple_subscribers(self):
        queue1 = event_bus.subscribe("test-blog-2")
        queue2 = event_bus.subscribe("test-blog-2")

        await event_bus.publish("test-blog-2", {"state": "completed"})

        event1 = await asyncio.wait_for(queue1.get(), timeout=1)
        event2 = await asyncio.wait_for(queue2.get(), timeout=1)

        assert event1["state"] == "completed"
        assert event2["state"] == "completed"

        event_bus.unsubscribe("test-blog-2", queue1)
        event_bus.unsubscribe("test-blog-2", queue2)

    async def test_unsubscribe_stops_events(self):
        queue = event_bus.subscribe("test-blog-3")
        event_bus.unsubscribe("test-blog-3", queue)

        await event_bus.publish("test-blog-3", {"state": "running"})

        assert queue.empty()
