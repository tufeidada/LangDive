import asyncio
import logging
from app.pipeline.steps import (
    step0_fetch_all_layers,
    step1_ai_ranking,
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

    # Step 0: Fetch candidates from all 3 layers into content_candidate table
    candidate_count = await step0_fetch_all_layers()
    logger.info(f"Step 0: {candidate_count} candidates fetched")

    # Step 1: AI ranking — select top 5 from candidates
    selected = await step1_ai_ranking()
    logger.info(f"Step 1: {len(selected)} selected for processing")

    if not selected:
        logger.warning("No content selected. Pipeline stopping.")
        return

    # Step 3: Extract full content text
    items = await step3_extract_content(selected)
    logger.info("Step 3: Content extracted")

    # Steps 4-6 combined: segment + annotate + summarize in ONE LLM call per article
    items = await step4_segment_annotate_summarize(items)
    logger.info("Step 4-6: Segmented + Annotated + Summarized (combined)")

    # Step 7: Generate TTS audio
    items = await step7_generate_tts(items)
    logger.info("Step 7: TTS audio generated")

    # Step 8: Translate video subtitles
    items = await step8_translate_videos(items)
    logger.info("Step 8: Videos translated")

    # Step 9: Store to database
    await step9_store(items)
    logger.info("=== Pipeline Complete ===")


def main():
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
