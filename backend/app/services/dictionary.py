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
