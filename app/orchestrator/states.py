from enum import Enum


class BlogState(str, Enum):
    IDLE = "idle"
    TOPIC_RESEARCH = "topic_research"
    NARRATIVE_PLANNING = "narrative_planning"
    WRITING = "writing"
    FACT_CHECKING = "fact_checking"
    HUMANIZING = "humanizing"
    SEO_CHECK = "seo_check"
    MCQ_GENERATION = "mcq_generation"
    IMAGE_SELECTION = "image_selection"
    COMPLETED = "completed"
    FAILED = "failed"


TRANSITIONS = {
    BlogState.IDLE: [BlogState.TOPIC_RESEARCH],
    BlogState.TOPIC_RESEARCH: [BlogState.NARRATIVE_PLANNING, BlogState.FAILED],
    BlogState.NARRATIVE_PLANNING: [BlogState.WRITING, BlogState.FAILED],
    BlogState.WRITING: [BlogState.FACT_CHECKING, BlogState.FAILED],
    BlogState.FACT_CHECKING: [BlogState.HUMANIZING, BlogState.WRITING, BlogState.FAILED],
    BlogState.HUMANIZING: [BlogState.SEO_CHECK, BlogState.WRITING, BlogState.FAILED],
    BlogState.SEO_CHECK: [BlogState.MCQ_GENERATION, BlogState.HUMANIZING, BlogState.FAILED],
    BlogState.MCQ_GENERATION: [BlogState.IMAGE_SELECTION, BlogState.FAILED],
    BlogState.IMAGE_SELECTION: [BlogState.COMPLETED, BlogState.FAILED],
}


AGENT_MAP = {
    BlogState.TOPIC_RESEARCH: "topic_scout",
    BlogState.NARRATIVE_PLANNING: "narrative_planner",
    BlogState.WRITING: "content_writer",
    BlogState.FACT_CHECKING: "fact_checker",
    BlogState.HUMANIZING: "humanizer",
    BlogState.SEO_CHECK: "seo_optimizer",
    BlogState.MCQ_GENERATION: "mcq_generator",
    BlogState.IMAGE_SELECTION: "image_selector",
}


PROGRESS_MAP = {
    BlogState.TOPIC_RESEARCH: 10,
    BlogState.NARRATIVE_PLANNING: 20,
    BlogState.WRITING: 40,
    BlogState.FACT_CHECKING: 55,
    BlogState.HUMANIZING: 70,
    BlogState.SEO_CHECK: 80,
    BlogState.MCQ_GENERATION: 90,
    BlogState.IMAGE_SELECTION: 95,
    BlogState.COMPLETED: 100,
}
