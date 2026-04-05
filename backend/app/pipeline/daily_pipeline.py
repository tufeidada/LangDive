import asyncio
import logging
from app.pipeline.steps import (
    step1_fetch_candidates,
    step2_filter_and_rank,
    step3_extract_content,
    step4_segment,
    step5_annotate,
    step6_generate_summary,
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

    items = await step4_segment(items)
    logger.info("Step 4: Segmented")

    items = await step5_annotate(items)
    logger.info("Step 5: Annotated")

    items = await step6_generate_summary(items)
    logger.info("Step 6: Summaries generated")

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
