"""
hallucination_detector.py

Hybrid hallucination detection for AI-generated responses.

Combines two independent signals:
  1. Semantic similarity  -> catches responses that drift off-topic
                              from the source/reference context.
  2. NLI entailment score -> catches responses that are topically close
                              but factually wrong / unsupported / contradictory.

Why two signals instead of one:
  - Semantic similarity alone can be fooled: "The mitochondria is the
    powerhouse of the cell" and "The mitochondria is the waste disposal
    of the cell" are highly similar in embedding space, but the second
    is false. NLI catches this because it checks logical support, not
    topical closeness.
  - NLI alone can be fooled by very short/vague responses. Similarity
    acts as a sanity check that the response is actually engaging with
    the source content at all.

This mirrors the multi-signal approach already used in
AnswerEvaluationEngine (TF-IDF cosine + Jaccard overlap) -- here we
swap in stronger, meaning-aware signals since hallucination detection
needs semantic understanding, not just lexical overlap.
"""

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class HallucinationResult:
    source_context: str
    generated_response: str
    semantic_similarity: float  # 0-1, higher = more topically aligned
    entailment_score: float  # 0-1, higher = source supports the claim
    contradiction_score: float  # 0-1, higher = source contradicts the claim
    neutral_score: float  # 0-1, source neither confirms nor denies
    hallucination_score: (
        float  # 0-1, final combined score (higher = more likely hallucinated)
    )
    is_hallucination: bool
    risk_level: str  # "low" | "medium" | "high"
    explanation: str

    def to_dict(self):
        return asdict(self)


class HallucinationDetector:
    """
    Usage:
        detector = HallucinationDetector()
        result = detector.evaluate(
            source_context="Paris is the capital of France.",
            generated_response="The capital of France is Paris."
        )
        print(result.is_hallucination, result.hallucination_score)
    """

    def __init__(
        self,
        semantic_model_name: str = "all-MiniLM-L6-v2",
        nli_model_name: str = "cross-encoder/nli-deberta-v3-small",
        # Weights for combining signals into the final hallucination score.
        # Entailment/contradiction matters more than raw similarity because
        # it's the actual factual-support signal.
        w_similarity: float = 0.3,
        w_nli: float = 0.7,
        hallucination_threshold: float = 0.30,
    ):
        self.w_similarity = w_similarity
        self.w_nli = w_nli
        self.threshold = hallucination_threshold

        # Lazy imports so the module can be imported/tested without the
        # (heavy) ML deps installed unless evaluate() is actually called.
        from sentence_transformers import CrossEncoder, SentenceTransformer

        self.embedder = SentenceTransformer(semantic_model_name)
        # CrossEncoder NLI models output logits for
        # [contradiction, entailment, neutral] (label order depends on model card;
        # nli-deberta-v3-small uses this order).
        self.nli_model = CrossEncoder(nli_model_name)

    # ---------- Signal 1: semantic similarity ----------
    def _semantic_similarity(self, source: str, response: str) -> float:
        embeddings = self.embedder.encode([source, response])
        a, b = embeddings[0], embeddings[1]
        cos_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
        # Clip to [0, 1] since cosine can be slightly negative for unrelated text
        return max(0.0, min(1.0, (cos_sim + 1) / 2))

    # ---------- Signal 2: NLI entailment ----------
    def _nli_scores(self, source: str, response: str) -> dict:
        # premise = source_context (what we know to be true / given)
        # hypothesis = generated_response (the claim we're checking)
        logits = self.nli_model.predict([(source, response)])[0]
        probs = self._softmax(logits)
        return {
            "contradiction": float(probs[0]),
            "entailment": float(probs[1]),
            "neutral": float(probs[2]),
        }

    @staticmethod
    def _softmax(x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    # ---------- Combine into final score ----------
    def evaluate(
        self, source_context: str, generated_response: str
    ) -> HallucinationResult:
        similarity = self._semantic_similarity(source_context, generated_response)
        nli = self._nli_scores(source_context, generated_response)

        # Hallucination risk rises when:
        #  - entailment is low (source doesn't support the claim), AND/OR
        #  - contradiction is high (source actively disagrees), AND/OR
        #  - similarity is low (response isn't even grounded in the source)
        non_support = 1 - nli["entailment"]
        nli_risk = (nli["contradiction"] * 0.6) + (non_support * 0.4)
        similarity_risk = 1 - similarity

        hallucination_score = (self.w_similarity * similarity_risk) + (
            self.w_nli * nli_risk
        )
        hallucination_score = round(min(1.0, max(0.0, hallucination_score)), 4)

        is_hallucination = hallucination_score >= self.threshold

        if hallucination_score < 0.3:
            risk_level = "low"
        elif hallucination_score < 0.6:
            risk_level = "medium"
        else:
            risk_level = "high"

        explanation = self._build_explanation(
            similarity, nli, hallucination_score, risk_level
        )

        return HallucinationResult(
            source_context=source_context,
            generated_response=generated_response,
            semantic_similarity=round(similarity, 4),
            entailment_score=round(nli["entailment"], 4),
            contradiction_score=round(nli["contradiction"], 4),
            neutral_score=round(nli["neutral"], 4),
            hallucination_score=hallucination_score,
            is_hallucination=is_hallucination,
            risk_level=risk_level,
            explanation=explanation,
        )

    @staticmethod
    def _build_explanation(similarity, nli, score, risk_level) -> str:
        if nli["contradiction"] > 0.5:
            reason = "the response contradicts the source context"
        elif nli["entailment"] < 0.3:
            reason = "the source context does not support this claim"
        elif similarity < 0.4:
            reason = "the response is not well-grounded in the source context"
        else:
            reason = "the response is consistent with the source context"
        return f"Risk={risk_level} (score={score}): {reason}."
