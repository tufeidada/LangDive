from datetime import datetime, timezone
from app.services.srs import calculate_next_review, SRS_INTERVALS

def test_grade_again_resets_to_level_0():
    result = calculate_next_review(grade=0, current_level=3, easy_streak=2)
    assert result["srs_level"] == 0
    assert result["easy_streak"] == 0

def test_grade_hard_keeps_level():
    result = calculate_next_review(grade=1, current_level=2, easy_streak=1)
    assert result["srs_level"] == 2
    assert result["easy_streak"] == 0

def test_grade_easy_increments_level():
    result = calculate_next_review(grade=2, current_level=0, easy_streak=0)
    assert result["srs_level"] == 1
    assert result["easy_streak"] == 1

def test_grade_easy_max_level():
    result = calculate_next_review(grade=2, current_level=5, easy_streak=4)
    assert result["srs_level"] == 5  # capped
    assert result["easy_streak"] == 5

def test_next_review_time_is_set():
    result = calculate_next_review(grade=2, current_level=0, easy_streak=0)
    assert result["next_review"] is not None
    assert result["next_review"] > datetime.now(timezone.utc)

def test_auto_hibernate_after_5_easy():
    result = calculate_next_review(grade=2, current_level=4, easy_streak=4)
    assert result["easy_streak"] == 5
    assert result["auto_hibernate"] is True
