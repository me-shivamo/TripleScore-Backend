from dataclasses import dataclass

DIFFICULTY_MULTIPLIER: dict[str, float] = {
    "EASY": 0.8,
    "MEDIUM": 1.0,
    "HARD": 1.3,
}

BENCHMARK_TIME_SECS = 90  # expected time per question

PRIOR_MASTERY = {
    "STRONG_SUBJECT": 0.55,
    "WEAK_SUBJECT": 0.25,
    "UNKNOWN": 0.30,
}


@dataclass
class AttemptSummary:
    is_correct: bool
    time_taken_secs: int
    difficulty: str


def calculate_mastery_score(attempts: list[AttemptSummary]) -> float:
    """
    Calculate a mastery score (0.0 – 1.0) for a chapter based on quiz attempts.

    Formula:
      base         = correct_count / total_attempted
      speed_factor = clamp(BENCHMARK_TIME / avg_time_secs, 0.5, 1.5)
      diff_mult    = average difficulty multiplier across attempts
      mastery      = clamp(base × speed_factor × diff_mult, 0, 1)
    """
    if not attempts:
        return 0.0

    total = len(attempts)
    correct = sum(1 for a in attempts if a.is_correct)
    total_time = sum(a.time_taken_secs for a in attempts)
    avg_time = total_time / total

    base = correct / total
    speed_factor = min(1.5, max(0.5, BENCHMARK_TIME_SECS / max(avg_time, 1)))
    avg_diff_mult = sum(DIFFICULTY_MULTIPLIER.get(a.difficulty, 1.0) for a in attempts) / total

    return min(1.0, max(0.0, base * speed_factor * avg_diff_mult))
