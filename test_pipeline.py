import asyncio, os, sys, time
sys.path.insert(0, '.')

from app.agents.topic_scout import TopicScoutAgent
from app.agents.narrative import NarrativePlannerAgent
from app.agents.writer import ContentWriterAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.humanizer import HumanizerAgent
from app.agents.seo_optimizer import SEOOptimizerAgent
from app.agents.mcq_generator import MCQGeneratorAgent

async def run_pipeline():
    topic = 'Digital India Programme and Rural Governance'
    start = time.time()

    print('1. Topic Scout...')
    scout = TopicScoutAgent()
    r1 = await scout.execute({'topic': topic})
    print(f'   Done: {r1.output.get("topic")}')

    print('2. Narrative Planner...')
    planner = NarrativePlannerAgent()
    r2 = await planner.execute({'topic': topic, 'research': r1.output})
    print(f'   Done: {r2.output.get("gs_paper")}, {len(r2.output.get("outline", []))} sections')

    print('3. Content Writer...')
    writer = ContentWriterAgent()
    r3 = await writer.execute({'topic': topic, 'narrative': r2.output, 'research': r1.output})
    print(f'   Done: {r3.output.get("title")}, {r3.output.get("word_count")} words')

    print('4. Fact Checker...')
    checker = FactCheckerAgent()
    r4 = await checker.execute({'topic': topic, 'draft': r3.output})
    print(f'   Done: verified={r4.output.get("verified")}')

    print('5. Humanizer...')
    humanizer = HumanizerAgent()
    r5 = await humanizer.execute({'draft': r3.output})
    print(f'   Done: {len(r5.output.get("changes_made", []))} changes')

    print('6. SEO Optimizer...')
    seo = SEOOptimizerAgent()
    content_for_seo = {'content': r5.output.get('content', ''), 'title': r5.output.get('title', '')}
    r6 = await seo.execute({'topic': topic, 'content': content_for_seo})
    print(f'   Done: SEO score={r6.output.get("seo_score")}')

    print('7. MCQ Generator...')
    mcq = MCQGeneratorAgent()
    r7 = await mcq.execute({'topic': topic, 'content': content_for_seo})
    print(f'   Done: {len(r7.output.get("questions", []))} MCQs')

    elapsed = time.time() - start
    print(f'\nPIPELINE COMPLETE in {elapsed:.1f}s')

asyncio.run(run_pipeline())
