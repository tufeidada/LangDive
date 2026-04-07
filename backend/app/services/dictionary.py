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
    """Estimate word level from ECDICT tags.

    ECDICT tags: zk=中考, gk=高考, cet4, cet6, ky=考研, ielts, toefl, gre
    Words with zk/gk are basic (even if also tagged ielts — ielts covers all levels).
    """
    entry = lookup_word(word)
    if not entry:
        return None
    tag = entry.get('tag', '')
    has_zk_gk = 'zk' in tag or 'gk' in tag

    if 'cet4' in tag or has_zk_gk:
        return 'CET-4'  # basic word (中考/高考/CET-4 level)
    elif 'cet6' in tag or 'ky' in tag:
        return 'CET-6'
    elif 'ielts' in tag:
        return 'IELTS'  # only if NOT also zk/gk
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

    # Extract words, filter noise
    raw_words = re.findall(r"[a-zA-Z']+", text.lower())
    # Skip: very short, possessives, contractions parts
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                  "have", "has", "had", "do", "does", "did", "will", "would", "could",
                  "should", "may", "might", "shall", "can", "need", "dare", "to", "of",
                  "in", "for", "on", "with", "at", "by", "from", "as", "into", "about",
                  "like", "through", "after", "over", "between", "out", "against", "during",
                  "without", "before", "under", "around", "among", "and", "but", "or",
                  "nor", "not", "so", "yet", "both", "either", "neither", "each", "every",
                  "all", "any", "few", "more", "most", "other", "some", "such", "no",
                  "only", "own", "same", "than", "too", "very", "just", "because", "if",
                  "when", "while", "where", "how", "what", "which", "who", "whom", "this",
                  "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
                  "me", "him", "her", "us", "them", "my", "your", "his", "its", "our",
                  "their", "mine", "yours", "hers", "ours", "theirs", "s", "t", "re", "ve",
                  "ll", "d", "m", "don", "doesn", "didn", "won", "wouldn", "couldn"}
    unique = {w for w in set(raw_words) if len(w) >= 3 and w not in stop_words}

    levels = {"CET-4": 0, "CET-6": 0, "IELTS": 0, "Advanced": 0, "Unknown": 0}
    for w in unique:
        level = get_word_level(w)
        if level:
            levels[level] += 1
        elif w in d:
            levels["CET-4"] += 1  # in dictionary but no level tag = basic
        else:
            # Unknown: likely proper noun or specialized term
            # Only count as hard if it looks like a real word (not a name/acronym)
            if w[0].islower() and len(w) > 4:
                levels["Advanced"] += 1
            # else: skip (proper nouns, acronyms, short unknown)

    total_classified = sum(levels.values()) or 1
    pct = {k: round(v / total_classified, 3) for k, v in levels.items()}

    # Estimate CEFR: based on CET-6 + IELTS + Advanced ratio
    hard_pct = pct.get("CET-6", 0) * 0.3 + pct.get("IELTS", 0) * 0.7 + pct.get("Advanced", 0) * 1.0
    if hard_pct > 0.25:
        cefr = "C1"
    elif hard_pct > 0.15:
        cefr = "B2"
    elif hard_pct > 0.08:
        cefr = "B1"
    else:
        cefr = "A2"

    # Difficulty score: 0 = easy, 1 = hard
    difficulty_score = round(min(1.0, hard_pct * 3), 2)

    return {
        "word_count": len(raw_words),
        "unique_words": len(unique),
        "level_distribution": levels,
        "level_pct": pct,
        "estimated_cefr": cefr,
        "difficulty_score": difficulty_score,
    }
