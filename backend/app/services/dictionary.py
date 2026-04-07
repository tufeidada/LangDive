import csv
import os
import logging

logger = logging.getLogger(__name__)

_dict: dict[str, dict] | None = None


def load_dictionary() -> dict[str, dict]:
    global _dict
    if _dict is not None:
        return _dict
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'stardict.csv')
    path = os.path.normpath(path)
    _dict = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row.get('word', '').lower().strip()
                if word:
                    _dict[word] = {
                        'word': word,
                        'phonetic': row.get('phonetic', ''),
                        'translation': row.get('translation', ''),  # Chinese meaning
                        'definition': row.get('definition', ''),     # English definition
                        'pos': row.get('pos', ''),                   # part of speech
                        'tag': row.get('tag', ''),                   # frequency tags like "cet4 cet6 ielts"
                        'exchange': row.get('exchange', ''),         # word forms
                    }
        logger.info(f"ECDICT loaded: {len(_dict)} entries")
    except FileNotFoundError:
        logger.warning(f"ECDICT stardict.csv not found at {path}, dictionary lookup disabled")
        _dict = {}
    return _dict


def lookup_word(word: str) -> dict | None:
    d = load_dictionary()
    return d.get(word.lower().strip())


def get_word_level(word: str) -> str | None:
    """Estimate word level from ECDICT tags."""
    entry = lookup_word(word)
    if not entry:
        return None
    tag = entry.get('tag', '')
    if 'cet4' in tag:
        return 'CET-4'
    elif 'cet6' in tag:
        return 'CET-6'
    elif 'ielts' in tag:
        return 'IELTS'
    elif 'gre' in tag or 'toefl' in tag:
        return 'Advanced'
    return None


def get_cet4_words_from_ecdict() -> set[str]:
    """Return the set of CET-4 words from ECDICT tag data."""
    d = load_dictionary()
    return {word for word, entry in d.items() if 'cet4' in entry.get('tag', '')}


def analyze_difficulty(text: str) -> dict:
    """Analyze text difficulty using ECDICT word level distribution.

    Returns: {
        "word_count": int,
        "unique_words": int,
        "level_distribution": {"CET-4": N, "CET-6": N, "IELTS": N, "Advanced": N, "Unknown": N},
        "level_pct": {"CET-4": 0.xx, ...},
        "estimated_cefr": "B1" | "B2" | "C1" | ...,
        "difficulty_score": 0.0-1.0,  # higher = harder
    }
    """
    import re
    d = load_dictionary()
    words = re.findall(r"[a-zA-Z']+", text.lower())
    unique = set(words)

    levels = {"CET-4": 0, "CET-6": 0, "IELTS": 0, "Advanced": 0, "Unknown": 0}
    for w in unique:
        if len(w) < 2:
            continue
        level = get_word_level(w)
        if level:
            levels[level] += 1
        elif w in d:
            levels["CET-4"] += 1  # in dictionary but no level tag = basic
        else:
            levels["Unknown"] += 1

    total_classified = sum(levels.values()) or 1
    pct = {k: round(v / total_classified, 3) for k, v in levels.items()}

    # Estimate CEFR based on distribution
    hard_pct = pct.get("IELTS", 0) + pct.get("Advanced", 0) + pct.get("Unknown", 0)
    if hard_pct > 0.3:
        cefr = "C1"
    elif hard_pct > 0.2:
        cefr = "B2"
    elif hard_pct > 0.1:
        cefr = "B1"
    else:
        cefr = "A2"

    # Difficulty score: 0 = easy, 1 = hard
    difficulty_score = round(min(1.0, hard_pct * 2.5), 2)

    return {
        "word_count": len(words),
        "unique_words": len(unique),
        "level_distribution": levels,
        "level_pct": pct,
        "estimated_cefr": cefr,
        "difficulty_score": difficulty_score,
    }
