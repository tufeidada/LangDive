from datetime import datetime, timedelta, timezone

# Level -> timedelta mapping (grade=2 "Easy" progression)
SRS_INTERVALS = {
    0: timedelta(days=1),
    1: timedelta(days=3),
    2: timedelta(days=7),
    3: timedelta(days=14),
    4: timedelta(days=30),
    5: timedelta(days=90),
}

# Grade=1 "Hard" interval
HARD_INTERVAL = timedelta(hours=6)

def calculate_next_review(
    grade: int,
    current_level: int,
    easy_streak: int,
) -> dict:
    now = datetime.now(timezone.utc)

    if grade == 0:  # Again
        return {
            "srs_level": 0,
            "easy_streak": 0,
            "next_review": now,  # immediate
            "auto_hibernate": False,
        }
    elif grade == 1:  # Hard
        return {
            "srs_level": current_level,
            "easy_streak": 0,
            "next_review": now + HARD_INTERVAL,
            "auto_hibernate": False,
        }
    else:  # Easy (grade == 2)
        new_level = min(current_level + 1, 5)
        new_streak = easy_streak + 1
        interval = SRS_INTERVALS.get(new_level, SRS_INTERVALS[5])
        return {
            "srs_level": new_level,
            "easy_streak": new_streak,
            "next_review": now + interval,
            "auto_hibernate": new_streak >= 5,
        }
