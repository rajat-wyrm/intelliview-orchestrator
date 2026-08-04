import re
import json
import logging
from typing import Optional

# Setup simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.config import settings
from app.database import log_evaluation

# Common English stop words to filter out for keyword matching
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", 
    "any", "are", "arent", "as", "at", "be", "because", "been", "before", "being", 
    "below", "between", "both", "but", "by", "cant", "cannot", "could", "couldnt", 
    "did", "didnt", "do", "does", "doesnt", "doing", "dont", "down", "during", 
    "each", "few", "for", "from", "further", "had", "hadnt", "has", "hasnt", 
    "have", "havent", "having", "he", "hed", "hell", "hes", "her", "here", 
    "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", 
    "id", "ill", "im", "ive", "if", "in", "into", "is", "isnt", "it", "its", 
    "itself", "lets", "me", "more", "most", "mustnt", "my", "myself", "no", 
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", 
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", 
    "shed", "shell", "shes", "should", "shouldnt", "so", "some", "such", "than", 
    "that", "thats", "the", "their", "theirs", "them", "themselves", "then", 
    "there", "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", 
    "this", "those", "through", "to", "too", "under", "until", "up", "very", 
    "was", "wasnt", "we", "wed", "well", "were", "weve", "werent", "what", 
    "whats", "when", "whens", "where", "wheres", "which", "while", "who", 
    "whos", "whom", "why", "whys", "with", "wont", "would", "wouldnt", "you", 
    "youd", "youll", "youre", "youve", "your", "yours", "yourself", "yourselves"
}

def clean_and_tokenize(text: str) -> set[str]:
    """Cleans text by removing punctuation, lowercasing, and splitting into non-stop-word tokens."""
    if not text:
        return set()
    cleaned = re.sub(r'[^a-zA-Z0-9\s-]', ' ', text.lower())
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
    return {t for t in tokens if t not in STOP_WORDS}

def detect_domain(question: str) -> str:
    """Detects the domain of the question (dsa, dbms, os) based on keyword overlap."""
    question_keywords = clean_and_tokenize(question)
    domain_scores = {domain: 0 for domain in settings.DOMAIN_KEYWORDS}
    
    for domain, keywords in settings.DOMAIN_KEYWORDS.items():
        overlap = question_keywords & keywords
        domain_scores[domain] = len(overlap)
        
    # Find domain with highest overlap
    best_domain = max(domain_scores, key=domain_scores.get)
    if domain_scores[best_domain] > 0:
        return best_domain
    return "dsa" # Default fallback domain

def run_rule_based_evaluation(question: str, answer: str, domain: str) -> dict:
    """Determines score and feedback based on keyword coverage and heuristics (fallback/pre-filter)."""
    question_keywords = clean_and_tokenize(question)
    answer_keywords = clean_and_tokenize(answer)
    
    # Calculate overlaps
    question_overlap = question_keywords & answer_keywords
    domain_overlap = settings.DOMAIN_KEYWORDS[domain] & answer_keywords
    
    overlap_ratio = len(question_overlap) / len(question_keywords) if question_keywords else 1.0
    domain_overlap_count = len(domain_overlap)
    
    # Heuristic scoring out of 10
    # 1. Question keyword overlap contributes up to 5 points
    q_score = overlap_ratio * 5.0
    # 2. Domain key concepts coverage contributes up to 5 points
    d_score = min(5.0, domain_overlap_count * 0.8)
    
    raw_score = q_score + d_score
    
    # Deduct points if the answer is too short (e.g. fewer than 5 content words)
    if len(answer_keywords) < 5:
        raw_score = min(raw_score, 3.0)
    
    score = round(raw_score, 1)
    
    # Feedback generation
    feedback_parts = [
        "LLM evaluation was unavailable; evaluated using rule-based keyword match.",
        f"Answer matched {len(question_overlap)} key terms from the question: {list(question_overlap)}.",
        f"Detected {domain_overlap_count} domain concepts relevant to {domain.upper()}: {list(domain_overlap)[:5]}."
    ]
    if len(answer_keywords) < 5:
        feedback_parts.append("Note: The response is extremely brief and may lack sufficient explanation.")
        
    return {
        "score": score,
        "feedback": " ".join(feedback_parts),
        "confidence": 0.45
    }

def call_gemini(prompt: str) -> Optional[dict]:
    """Helper to configure and invoke Gemini API using google-generativeai."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return None

def call_openai(prompt: str) -> Optional[dict]:
    """Helper to configure and invoke OpenAI API."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a strict, objective, and expert technical interviewer evaluation bot that returns only structured JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None

def evaluate_answer(question: str, answer: str, domain: Optional[str] = None) -> dict:
    """Core evaluation pipeline combining rule-based filtering and LLM evaluation."""
    # 1. Edge Case: Empty Answer
    stripped_answer = answer.strip() if answer else ""
    if not stripped_answer:
        result = {
            "score": 0.0,
            "feedback": "No answer was provided (empty input).",
            "confidence": 1.0
        }
        # Log to database
        _log_result(question, answer or "", domain or "unknown", result, "rule_based", None)
        return result
        
    # 2. Determine Domain
    if domain:
        domain = domain.strip().lower()
        if domain not in settings.DOMAIN_KEYWORDS:
            domain = detect_domain(question)
    else:
        domain = detect_domain(question)
        
    # 3. Rule-Based Relevance Check
    question_keywords = clean_and_tokenize(question)
    answer_keywords = clean_and_tokenize(answer)
    
    question_overlap = question_keywords & answer_keywords
    domain_overlap = settings.DOMAIN_KEYWORDS[domain] & answer_keywords
    
    # If there is absolutely zero keyword overlap with either the question or the domain keywords, 
    # the answer is flagged as completely irrelevant.
    if not question_overlap and not domain_overlap:
        result = {
            "score": 0.0,
            "feedback": f"The answer is completely irrelevant to the question or the domain of {domain.upper()}.",
            "confidence": 1.0
        }
        _log_result(question, answer, domain, result, "rule_based", None)
        return result
        
    # 4. Formulate Prompt for LLM
    prompt = f"""
Evaluate the candidate's answer to the technical question in the domain "{domain}".

Question: {question}
Candidate's Answer: {answer}

Perform a strict evaluation based on:
1. Correctness: Is the explanation technically accurate?
2. Completeness: Did the candidate mention all necessary components or steps required by the question?
3. Relevance: Is the answer directly addressing the question without off-topic filler?

Constraints to avoid hallucination:
- Evaluate only what is written in the answer. Do not assume or guess the candidate's intent.
- Do not make up facts or feedback details.
- Provide a score from 0.0 to 10.0.
- Provide objective, concise constructive feedback (max 3 sentences) specifying what is correct and what is missing or incorrect.
- Provide a confidence score from 0.0 to 1.0 based on how well the candidate's answer could be evaluated (e.g. 0.9 for detailed responses, lower for ambiguous or very short responses).

You MUST output ONLY a valid JSON object matching the schema below:
{{
  "score": 7.5,
  "feedback": "The explanation of the concept is correct, but the answer fails to mention the time complexity of the operation.",
  "confidence": 0.85
}}
"""

    # 5. Try calling LLM (respecting configured preferences)
    llm_result = None
    used_provider = None
    
    # Try primary provider first
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        llm_result = call_openai(prompt)
        if llm_result:
            used_provider = "openai"
    elif settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        llm_result = call_gemini(prompt)
        if llm_result:
            used_provider = "gemini"
        
    # Fallback to secondary provider if primary key was missing or failed
    if not llm_result:
        if settings.GEMINI_API_KEY:
            logger.info("Attempting fallback to Gemini API...")
            llm_result = call_gemini(prompt)
            if llm_result:
                used_provider = "gemini"
        elif settings.OPENAI_API_KEY:
            logger.info("Attempting fallback to OpenAI API...")
            llm_result = call_openai(prompt)
            if llm_result:
                used_provider = "openai"
            
    # 6. Process LLM result if available, otherwise degrade to rule-based evaluation
    if llm_result:
        try:
            score = float(llm_result.get("score", 0.0))
            # Bound the score to [0.0, 10.0]
            score = max(0.0, min(10.0, score))
            feedback = str(llm_result.get("feedback", "No feedback provided."))
            confidence = float(llm_result.get("confidence", 0.7))
            confidence = max(0.0, min(1.0, confidence))
            
            result = {
                "score": round(score, 1),
                "feedback": feedback,
                "confidence": round(confidence, 2)
            }
            _log_result(question, answer, domain, result, "llm", used_provider)
            return result
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse LLM result fields: {e}")
            
    # 7. Fallback to rule-based scorer
    result = run_rule_based_evaluation(question, answer, domain)
    _log_result(question, answer, domain, result, "rule_based", None)
    return result


def _log_result(question: str, answer: str, domain: str, result: dict, method: str, provider: Optional[str]):
    """Safely log evaluation result to the database. Never raises."""
    try:
        log_evaluation(
            question=question,
            answer=answer,
            domain=domain,
            score=result["score"],
            feedback=result["feedback"],
            confidence=result["confidence"],
            evaluation_method=method,
            llm_provider=provider,
        )
    except Exception as e:
        logger.error(f"Failed to log evaluation to database: {e}")
