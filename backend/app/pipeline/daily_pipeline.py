import asyncio
import logging
from app.pipeline.steps import (
    step0_fetch_all_layers,
    step05_preextract_and_filter,
    step1_ai_ranking,
    step3_extract_content,
    step4_segment_annotate_summarize,
    step7_generate_tts,
    step8_translate_videos,
    step9_store,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def _log_pipeline_result(status: str, details: dict):
    """Log pipeline run result to event_log for dashboard/alerting."""
    from app.database import AsyncSessionLocal
    from app.models import EventLog
    try:
        async with AsyncSessionLocal() as session:
            session.add(EventLog(
                event_type="pipeline_run",
                extra_json={"status": status, **details},
            ))
            await session.commit()
    except Exception:
        pass  # don't fail on logging

    if status == "error":
        with open("/tmp/langdive-alert.txt", "a") as f:
            from datetime import datetime
            f.write(f"[{datetime.now()}] Pipeline ERROR: {details.get('error', 'unknown')}\n")


async def run_pipeline():
    logger.info("=== LangDive Daily Pipeline Start ===")
    items = None
    try:
        # Step 0: Fetch candidates from all 3 layers into content_candidate table
        candidate_count = await step0_fetch_all_layers()
        logger.info(f"Step 0: {candidate_count} candidates fetched")

        # Step 0.5: Pre-extract article content, filter junk, compute difficulty scores
        passed = await step05_preextract_and_filter()
        logger.info(f"Step 0.5: {passed} candidates passed quality filter")

        # Step 1: AI ranking — select top 5 from candidates (using pre-computed scores)
        selected = await step1_ai_ranking()
        logger.info(f"Step 1: {len(selected)} selected for processing")

        if not selected:
            logger.warning("No content selected. Pipeline stopping.")
            await _log_pipeline_result("success", {"items_stored": 0})
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
        # Log success to event_log
        await _log_pipeline_result("success", {"items_stored": len(items) if items else 0})
    except Exception as e:
        logger.error(f"Pipeline FAILED: {e}")
        await _log_pipeline_result("error", {"error": str(e)[:500]})
        raise


def main():
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
