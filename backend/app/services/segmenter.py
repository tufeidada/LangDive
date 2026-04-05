import json
import logging
from app.services.llm import call_llm

logger = logging.getLogger(__name__)

SEGMENT_SYSTEM_PROMPT = "You are a content segmentation assistant for a language learning system."

SEGMENT_USER_PROMPT = """Split this content into semantic segments for language learning.
- Each segment covers ONE coherent topic/argument
- Segments can vary in length (short tangent = 100 words, deep discussion = 600+ words)
- Do NOT force-split a cohesive argument
- {video_instruction}
- Give each segment a short English title

Return ONLY JSON array:
[{{"segment_index": 0, "title": "...", "start_time": null, "end_time": null, "text_en": "..."}}]

Content:
{text}"""

async def segment_content(
    text: str,
    content_type: str = "article",
    word_threshold: int = 800,
) -> list[dict]:
    word_count = len(text.split())
    if word_count <= word_threshold:
        return [{
            "segment_index": 0,
            "title": "Full Content",
            "start_time": None,
            "end_time": None,
            "text_en": text,
        }]

    video_instruction = (
        "For video: align boundaries to nearest subtitle timestamp"
        if content_type == "video"
        else "This is an article, start_time and end_time should be null"
    )
    prompt = SEGMENT_USER_PROMPT.format(
        video_instruction=video_instruction,
        text=text[:15000],
    )
    response = await call_llm(SEGMENT_SYSTEM_PROMPT, prompt)
    try:
        segments = json.loads(response)
        return segments
    except json.JSONDecodeError:
        logger.error("Failed to parse segmentation response")
        return [{
            "segment_index": 0,
            "title": "Full Content",
            "start_time": None,
            "end_time": None,
            "text_en": text,
        }]
