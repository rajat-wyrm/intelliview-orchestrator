"""Reusable decision logic for adaptive interview difficulty."""

from typing import Literal

Difficulty = Literal["easy", "medium", "hard"]


def get_next_difficulty(score: float) -> Difficulty:
    """Return the next difficulty for a candidate score on a 0–10 scale."""
    if score > 8:
        return "hard"
    if score < 5:
        return "easy"
    return "medium"
