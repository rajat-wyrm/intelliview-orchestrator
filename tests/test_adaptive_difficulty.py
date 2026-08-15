from workers.adaptive_difficulty import get_next_difficulty


def test_high_scores_return_hard():
    assert get_next_difficulty(9) == "hard"
    assert get_next_difficulty(10) == "hard"


def test_low_scores_return_easy():
    assert get_next_difficulty(4) == "easy"
    assert get_next_difficulty(0) == "easy"


def test_boundary_scores_return_medium():
    assert get_next_difficulty(5) == "medium"
    assert get_next_difficulty(8) == "medium"
