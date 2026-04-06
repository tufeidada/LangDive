import asyncio
import logging
from app.pipeline.steps import (
    step1_fetch_candidates,
    step2_filter_and_rank,
    step3_extract_content,
    step4_segment_annotate_summarize,
    step7_generate_tts,
    step8_translate_videos,
    step9_store,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run_pipeline():
    logger.info("=== LangDive Daily Pipeline Start ===")

    candidates = await step1_fetch_candidates()
    logger.info(f"Step 1: {len(candidates)} candidates")

    selected = await step2_filter_and_rank(candidates)
    logger.info(f"Step 2: {len(selected)} selected")

    items = await step3_extract_content(selected)
    logger.info("Step 3: Content extracted")

    # Combined: segment + annotate + summarize in ONE LLM call per article
    items = await step4_segment_annotate_summarize(items)
    logger.info("Step 4-6: Segmented + Annotated + Summarized (combined)")

    items = await step7_generate_tts(items)
    logger.info("Step 7: TTS audio generated")

    items = await step8_translate_videos(items)
    logger.info("Step 8: Videos translated")

    await step9_store(items)
    logger.info("=== Pipeline Complete ===")


def main():
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
