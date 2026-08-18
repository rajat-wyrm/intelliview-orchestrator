import logging

logger = logging.getLogger(__name__)

_model = None
_model_loaded = False


def _get_model():
    """Lazily load the sentence-transformer model, with graceful fallback."""
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as exc:  # pragma: no cover - depends on env
        logger.warning(
            "SentenceTransformer unavailable, semantic similarity disabled: %s", exc
        )
        _model = None
    return _model


def calculate_semantic_similarity(reference: str, candidate: str) -> float:
    """
    Returns semantic similarity score between 0.0 and 1.0
    """

    if not reference or not candidate:
        return 0.0

    model = _get_model()
    if model is None:
        return 0.0

    from sklearn.metrics.pairwise import cosine_similarity

    embeddings = model.encode([reference, candidate], convert_to_numpy=True)

    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

    return round(float(similarity), 4)
