QUALITY_EVALUATION_PROMPT = (
    "You are an expert technical interviewer. Evaluate this candidate answer. "
    "Return a JSON object with keys: overall_quality_score (0-100), "
    "relevance (0-1), completeness (0-1), clarity (0-1), feedback (string)."
)

TECHNICAL_ACCURACY_PROMPT = (
    "You are a technical interviewer evaluating a candidate's answer. "
    "Return a JSON object with keys: accuracy_score (0-100), "
    "correct_concepts_count (int), incorrect_concepts_count (int), "
    "knowledge_gaps (list of strings)."
)

COMMUNICATION_EVALUATION_PROMPT = (
    "Evaluate the candidate's communication quality. "
    "Return a JSON object with keys: clarity_score (0-100), "
    "professionalism (0-100), confidence_level (0-1), "
    "pace_appropriateness (0-1)."
)

COACHING_GENERATION_PROMPT = (
    "You are an expert AI interview coach. Analyze the candidate's actual interview "
    "performance data (including questions, answers, scores, and feedback) and provide "
    "personalized coaching. "
    "Return a JSON object with keys: "
    "strengths (list of strings), "
    "weaknesses (list of strings), "
    "communication_feedback (string or object), "
    "topics_requiring_improvement (list of strings), "
    "recommendations (list of strings), "
    "suggestions_for_future_answers (list of strings), "
    "sample_improved_answers (list of strings)."
)
