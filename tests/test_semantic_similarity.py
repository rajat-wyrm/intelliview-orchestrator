import sys
import types

import numpy as np
import pytest

import workers.semantic_similarity as semantic_similarity

# The vectors below are deterministic fixtures used only by the offline
# benchmark. They allow the test to exercise the real cosine-similarity
# calculation without downloading an embedding model in CI.
_OFFLINE_EMBEDDINGS = {
    # Paraphrase examples: expected cosine similarity = 0.90
    "The doctor prescribed medication.": np.array([1.0, 0.0]),
    "The physician prescribed medicine.": np.array([0.9, np.sqrt(1 - 0.9**2)]),
    "She completed the assignment yesterday.": np.array([1.0, 0.0]),
    "She finished the task the day before.": np.array([0.9, np.sqrt(1 - 0.9**2)]),
    "The meeting has been moved to Friday.": np.array([1.0, 0.0]),
    "The meeting was rescheduled for Friday.": np.array([0.9, np.sqrt(1 - 0.9**2)]),
    "The cat is sleeping on the sofa.": np.array([1.0, 0.0]),
    "A cat is asleep on the couch.": np.array([0.9, np.sqrt(1 - 0.9**2)]),
    # Similar examples: expected cosine similarity = 0.60
    "The company increased its revenue this year.": np.array([1.0, 0.0]),
    "The business reported higher earnings this year.": np.array(
        [0.6, np.sqrt(1 - 0.6**2)]
    ),
    "The employee requested vacation leave.": np.array([1.0, 0.0]),
    "The worker asked for time off.": np.array([0.6, np.sqrt(1 - 0.6**2)]),
    # Different examples: expected cosine similarity = 0.05
    "The stock market closed higher today.": np.array([0.05, np.sqrt(1 - 0.05**2)]),
    "I enjoy playing football on weekends.": np.array([1.0, 0.0]),
    "The weather forecast predicts heavy rain tomorrow.": np.array(
        [0.05, np.sqrt(1 - 0.05**2)]
    ),
    "The database backup completed successfully.": np.array([1.0, 0.0]),
    "The restaurant is serving dinner tonight.": np.array([0.05, np.sqrt(1 - 0.05**2)]),
    "He bought a new laptop yesterday.": np.array([1.0, 0.0]),
    "She planted flowers in the garden.": np.array([0.05, np.sqrt(1 - 0.05**2)]),
}


class _OfflineSemanticModel:
    """Stub that replaces SentenceTransformer during the offline benchmark.

    Vectors in _OFFLINE_EMBEDDINGS are deterministic test fixtures constructed
    to yield known cosine-similarity values. They are NOT real model-generated
    embeddings and do not reflect what all-MiniLM-L6-v2 would actually produce.
    """

    def encode(self, texts, convert_to_numpy=True):
        missing = [t for t in texts if t not in _OFFLINE_EMBEDDINGS]
        if missing:
            raise KeyError(
                f"_OfflineSemanticModel: no fixture vector defined for: {missing}. "
                "Add an entry to _OFFLINE_EMBEDDINGS to use this sentence in a test."
            )
        return np.array([_OFFLINE_EMBEDDINGS[text] for text in texts])


# ---------------------------------------------------------------------------
# Offline sklearn stub
# ---------------------------------------------------------------------------
# workers/semantic_similarity.py does `from sklearn.metrics.pairwise import
# cosine_similarity` lazily, after _get_model() returns.  When sklearn is not
# installed in the local environment (it is a transitive dep of
# sentence-transformers and present in CI), the import fails even though the
# benchmark never touches the real model.  The fixture below injects a minimal
# stub so that all benchmark tests run offline regardless of whether sklearn
# is installed.


@pytest.fixture(autouse=True)
def _stub_sklearn_if_missing():
    """Ensure `from sklearn.metrics.pairwise import cosine_similarity` resolves
    without a real sklearn installation.  Skipped when sklearn is already present."""
    if "sklearn" in sys.modules:
        yield
        return

    def _cosine_similarity(A, B):
        """Minimal cosine similarity matching sklearn's interface: accepts list-of-arrays."""
        a = np.array(A[0], dtype=float)
        b = np.array(B[0], dtype=float)
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        result = float(np.dot(a, b) / denom) if denom > 0 else 0.0
        return np.array([[result]])

    # Build the minimal module tree sklearn.metrics.pairwise
    sklearn_mod = types.ModuleType("sklearn")
    metrics_mod = types.ModuleType("sklearn.metrics")
    pairwise_mod = types.ModuleType("sklearn.metrics.pairwise")
    pairwise_mod.cosine_similarity = _cosine_similarity
    metrics_mod.pairwise = pairwise_mod
    sklearn_mod.metrics = metrics_mod

    sys.modules.setdefault("sklearn", sklearn_mod)
    sys.modules.setdefault("sklearn.metrics", metrics_mod)
    sys.modules.setdefault("sklearn.metrics.pairwise", pairwise_mod)

    yield

    # Clean up only the keys we added (don't remove if they existed before)
    for key in ("sklearn", "sklearn.metrics", "sklearn.metrics.pairwise"):
        sys.modules.pop(key, None)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


SEMANTIC_SIMILARITY_CASES = [
    pytest.param(
        "The doctor prescribed medication.",
        "The physician prescribed medicine.",
        0.85,
        0.95,
        id="paraphrase-doctor-physician",
    ),
    pytest.param(
        "She completed the assignment yesterday.",
        "She finished the task the day before.",
        0.85,
        0.95,
        id="paraphrase-assignment-task",
    ),
    pytest.param(
        "The meeting has been moved to Friday.",
        "The meeting was rescheduled for Friday.",
        0.85,
        0.95,
        id="paraphrase-meeting-rescheduled",
    ),
    pytest.param(
        "The cat is sleeping on the sofa.",
        "A cat is asleep on the couch.",
        0.85,
        0.95,
        id="paraphrase-cat-sleeping",
    ),
    pytest.param(
        "The company increased its revenue this year.",
        "The business reported higher earnings this year.",
        0.55,
        0.65,
        id="similar-revenue-earnings",
    ),
    pytest.param(
        "The employee requested vacation leave.",
        "The worker asked for time off.",
        0.55,
        0.65,
        id="similar-vacation-time-off",
    ),
    pytest.param(
        "The cat is sleeping on the sofa.",
        "The stock market closed higher today.",
        0.00,
        0.10,
        id="different-cat-stock-market",
    ),
    pytest.param(
        "I enjoy playing football on weekends.",
        "The weather forecast predicts heavy rain tomorrow.",
        0.00,
        0.10,
        id="different-football-weather",
    ),
    pytest.param(
        "The database backup completed successfully.",
        "The restaurant is serving dinner tonight.",
        0.00,
        0.10,
        id="different-database-restaurant",
    ),
    pytest.param(
        "He bought a new laptop yesterday.",
        "She planted flowers in the garden.",
        0.00,
        0.10,
        id="different-laptop-flowers",
    ),
]


@pytest.mark.unit
@pytest.mark.parametrize(
    "reference,candidate,min_score,max_score",
    SEMANTIC_SIMILARITY_CASES,
)
def test_semantic_similarity_benchmark(
    monkeypatch,
    reference,
    candidate,
    min_score,
    max_score,
):
    monkeypatch.setattr(
        semantic_similarity,
        "_get_model",
        lambda: _OfflineSemanticModel(),
    )

    score = semantic_similarity.calculate_semantic_similarity(reference, candidate)

    assert min_score <= score <= max_score, (
        f"Unexpected semantic similarity score {score:.4f} "
        f"for pair: {reference!r} / {candidate!r}. "
        f"Expected range: {min_score:.2f}-{max_score:.2f}"
    )


@pytest.mark.unit
def test_empty_input_returns_zero_without_loading_model(monkeypatch):
    """Empty reference triggers the early-exit guard before _get_model() is called.

    Verifies that calculate_semantic_similarity short-circuits on falsy input
    and never reaches the model-loading code path.
    """

    def fail_if_model_is_loaded():
        pytest.fail("The benchmark attempted to load an external embedding model")

    monkeypatch.setattr(
        semantic_similarity,
        "_get_model",
        fail_if_model_is_loaded,
    )

    assert semantic_similarity.calculate_semantic_similarity("", "candidate") == 0.0
