import pytest
from app.orchestrator.states import BlogState, TRANSITIONS, AGENT_MAP, PROGRESS_MAP


class TestBlogStates:
    def test_all_states_have_transitions(self):
        for state in BlogState:
            if state not in (BlogState.COMPLETED, BlogState.FAILED):
                assert state in TRANSITIONS, f"Missing transition for {state}"

    def test_all_states_have_agents(self):
        for state in BlogState:
            if state not in (BlogState.IDLE, BlogState.COMPLETED, BlogState.FAILED):
                assert state in AGENT_MAP, f"Missing agent for {state}"

    def test_all_states_have_progress(self):
        for state in BlogState:
            if state not in (BlogState.IDLE, BlogState.FAILED):
                assert state in PROGRESS_MAP, f"Missing progress for {state}"

    def test_progress_is_monotonic(self):
        ordered_states = [
            BlogState.TOPIC_RESEARCH,
            BlogState.NARRATIVE_PLANNING,
            BlogState.WRITING,
            BlogState.FACT_CHECKING,
            BlogState.HUMANIZING,
            BlogState.SEO_CHECK,
            BlogState.MCQ_GENERATION,
            BlogState.IMAGE_SELECTION,
            BlogState.COMPLETED,
        ]
        for i in range(len(ordered_states) - 1):
            current = PROGRESS_MAP[ordered_states[i]]
            next_val = PROGRESS_MAP[ordered_states[i + 1]]
            assert current < next_val, f"Progress not increasing: {ordered_states[i]} ({current}) >= {ordered_states[i+1]} ({next_val})"

    def test_feedback_loops_allowed(self):
        assert BlogState.WRITING in TRANSITIONS[BlogState.FACT_CHECKING]
        assert BlogState.HUMANIZING in TRANSITIONS[BlogState.SEO_CHECK]
        assert BlogState.WRITING in TRANSITIONS[BlogState.HUMANIZING]

    def test_all_states_can_fail(self):
        for state, targets in TRANSITIONS.items():
            if state != BlogState.IDLE:
                assert BlogState.FAILED in targets, f"{state} cannot transition to FAILED"

    def test_completed_and_failed_are_terminal(self):
        assert BlogState.COMPLETED not in TRANSITIONS
        assert BlogState.FAILED not in TRANSITIONS
