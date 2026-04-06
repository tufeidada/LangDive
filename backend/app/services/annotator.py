import json
import logging
import os
from app.services.llm import call_llm

logger = logging.getLogger(__name__)

_cet4_set: set[str] | None = None

def load_cet4_set() -> set[str]:
    global _cet4_set
    if _cet4_set is not None:
        return _cet4_set
    # Start with the local txt word list
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cet4_words.txt")
    path = os.path.normpath(path)
    try:
        with open(path, "r") as f:
            txt_words = {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        logger.warning("CET-4 word list not found, falling back to ECDICT only")
        txt_words = set()
    # Merge with ECDICT tag-based CET-4 words for broader coverage
    try:
        from app.services.dictionary import get_cet4_words_from_ecdict
        ecdict_cet4 = get_cet4_words_from_ecdict()
        _cet4_set = txt_words | ecdict_cet4
        logger.info(f"CET-4 set: {len(txt_words)} from txt + {len(ecdict_cet4)} from ECDICT = {len(_cet4_set)} total")
    except Exception as e:
        logger.warning(f"Could not load ECDICT CET-4 words: {e}")
        _cet4_set = txt_words
    return _cet4_set

ANNOTATE_SYSTEM = """You are an English vocabulary annotator for a Chinese learner at B1-B2 level
with a baseline of ~3,500 words (CET-4 level).

Identify unfamiliar words. For each, assess level:
- CET-4: ~4,500 word range
- CET-6: ~6,500 word range
- IELTS: ~8,000 word range
- Advanced: beyond IELTS

Return ONLY JSON array, sorted by freq_in_content DESC:
[{"word":"...", "ipa":"...", "freq_in_content":8, "importance_score":0.9,
  "meaning_zh":"...", "detail_zh":"...", "example_en":"...", "example_zh":"...",
  "level":"IELTS"}]"""

async def annotate_vocabulary(text: str) -> list[dict]:
    response = await call_llm(ANNOTATE_SYSTEM, f"Annotate vocabulary in:\n\n{text[:10000]}")
    try:
        content = response.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        return json.loads(content)
    except (json.JSONDecodeError, IndexError):
        logger.error(f"Failed to parse annotation response: {response[:200]}")
        return []

async def annotate_custom_word(word: str, context_sentence: str) -> dict | None:
    prompt = f'Word: "{word}" | Context: "{context_sentence}"\nReturn ONLY JSON:\n{{"word":"...", "ipa":"...", "meaning_zh":"...", "detail_zh":"...", "example_en":"...", "example_zh":"...", "level":"CET-4|CET-6|IELTS|Advanced"}}'
    system = "You are an English vocabulary annotator for a Chinese learner."
    response = await call_llm(system, prompt)
    try:
        content = response.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        return json.loads(content)
    except (json.JSONDecodeError, IndexError):
        logger.error(f"Failed to parse custom word lookup: {response[:200]}")
        return None
