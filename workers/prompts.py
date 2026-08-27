"""
Prompt templates for the automated interview preparation platform.

This module contains prompt definitions only.
It intentionally does not contain LLM clients, API wrappers, or
prompt-execution logic.
"""

# ---------------------------------------------------------------------------
# Evaluation Prompts
# ---------------------------------------------------------------------------

QUALITY_EVALUATION_PROMPT = (
    "You are an expert technical interviewer. "
    "Evaluate this candidate answer. "
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

BEHAVIORAL_STAR_PROMPT = (
    "You are an expert behavioral interviewer. "
    "Generate behavioral interview questions that encourage candidates "
    "to answer using the STAR method: Situation, Task, Action, and Result. "
    "Questions must ask for a specific real experience rather than a "
    "hypothetical situation or a general opinion. "
    "When evaluating a candidate's answer, check whether it provides a "
    "concrete Situation, Task, Action, and Result. "
    "If the answer already provides a sufficiently concrete STAR example, "
    "do not generate an unnecessary follow-up. "
    "Evaluate the candidate answer provided below. "
    "Candidate answer: {candidate_answer} "
    "Return a JSON object with keys: "
    "domain (string), question (string), "
    "is_star_complete (boolean), follow_up_question (string or null)."
)

BEHAVIORAL_PROMPT_TEMPLATE = {
    "domain": "behavioral",
    "prompt_template": BEHAVIORAL_STAR_PROMPT,
}

# ---------------------------------------------------------------------------
# Data Science Prompt Templates
# ---------------------------------------------------------------------------

DATA_SCIENCE_PROMPTS = [
    {
        "domain": "data-science",
        "difficulty": "easy",
        "prompt_template": (
            "You are an expert Data Science interviewer. "
            "Generate one easy-level statistics interview question for a beginner. "
            "Focus on fundamental concepts such as mean, median, mode, variance, "
            "standard deviation, probability, or basic distributions. "
            "The question must be clear, technically accurate, relevant to Data Science, "
            "and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "easy",
        "prompt_template": (
            "You are an expert Machine Learning interviewer. "
            "Generate one easy-level Machine Learning interview question. "
            "Focus on fundamental concepts such as supervised learning, "
            "unsupervised learning, training data, testing data, features, labels, "
            "or basic model evaluation. "
            "The question should be suitable for a beginner and must be "
            "clear, technically accurate, and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "easy",
        "prompt_template": (
            "You are a Data Science interviewer. "
            "Generate one easy-level question about data preprocessing. "
            "Focus on practical fundamentals such as missing values, duplicate data, "
            "categorical encoding, scaling, or basic data cleaning. "
            "The question should test understanding rather than memorization "
            "and must be clear, relevant, and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "medium",
        "prompt_template": (
            "You are an experienced Machine Learning interviewer. "
            "Generate one medium-level Machine Learning question involving "
            "model selection, feature engineering, overfitting, cross-validation, "
            "or evaluation metrics. "
            "Require the candidate to explain their reasoning or apply the concept "
            "to a practical situation. "
            "The question must be technically accurate, relevant, and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "medium",
        "prompt_template": (
            "You are an experienced Data Science interviewer. "
            "Generate one medium-level statistics question that requires "
            "interpretation or practical application. "
            "Focus on topics such as hypothesis testing, confidence intervals, "
            "correlation, probability distributions, sampling, or statistical significance. "
            "The question should require reasoning and must be clear, relevant, "
            "technically accurate, and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "medium",
        "prompt_template": (
            "You are a Data Science interviewer. "
            "Generate one medium-level practical Machine Learning scenario. "
            "Ask the candidate to determine an appropriate approach for a problem "
            "involving data preprocessing, class imbalance, model evaluation, "
            "feature selection, or model improvement. "
            "The question should test practical decision-making and must be "
            "technically accurate and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "hard",
        "prompt_template": (
            "You are a senior Machine Learning interviewer. "
            "Generate one hard-level Machine Learning question that tests "
            "advanced reasoning and trade-offs. "
            "Focus on topics such as model bias and variance, imbalanced datasets, "
            "model interpretability, optimization, scalability, data leakage, "
            "or production model failures. "
            "The question should require a detailed technical explanation "
            "and must be challenging, relevant, and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "hard",
        "prompt_template": (
            "You are a senior Data Science interviewer. "
            "Generate one hard-level statistics question involving advanced "
            "statistical reasoning, assumptions, uncertainty, experimentation, "
            "causal reasoning, or statistical inference. "
            "The question should require the candidate to analyze a situation, "
            "identify assumptions, and justify their approach. "
            "Ensure the question is technically accurate, challenging, "
            "and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "hard",
        "prompt_template": (
            "You are a senior Data Science interviewer. "
            "Generate one hard-level real-world Data Science case-study question. "
            "Present a realistic business problem with incomplete or ambiguous "
            "information. Require the candidate to reason about data collection, "
            "preprocessing, feature engineering, model selection, evaluation, "
            "business metrics, and trade-offs. "
            "The question must be realistic, challenging, technically relevant, "
            "and non-repetitive."
        ),
    },
    {
        "domain": "data-science",
        "difficulty": "hard",
        "prompt_template": (
            "You are a senior Machine Learning interviewer. "
            "Generate one hard-level production Machine Learning case-study question. "
            "The scenario should involve challenges such as model drift, "
            "data distribution changes, latency, scalability, monitoring, "
            "retraining, or unreliable predictions. "
            "Require the candidate to propose a solution and explain the trade-offs. "
            "The question must test advanced problem-solving and be "
            "technically accurate and non-repetitive."
        ),
    },
]


# ---------------------------------------------------------------------------
# Marketing & Sales Prompt Templates
# ---------------------------------------------------------------------------

MARKETING_SALES_PROMPTS = [
    {
        "domain": "marketing-sales",
        "prompt_template": (
            "You are an expert marketing and sales interviewer. "
            "Generate one realistic sales pitch interview question. "
            "Give the candidate a specific product, target customer, and selling situation "
            "and ask them to explain how they would pitch the product. "
            "The question should test customer understanding, value proposition, "
            "persuasion, and objection handling. "
            "Make the scenario realistic and avoid generic interview questions."
        ),
    },
    {
        "domain": "marketing-sales",
        "prompt_template": (
            "You are an expert marketing interviewer. "
            "Generate one campaign case-study interview question involving an "
            "underperforming marketing campaign. "
            "Provide realistic information such as the target audience, campaign goal, "
            "and performance issue, then ask the candidate how they would diagnose "
            "the problem and improve the campaign. "
            "Test analytical thinking, audience segmentation, channel selection, "
            "and campaign optimization. "
            "Avoid generic questions."
        ),
    },
    {
        "domain": "marketing-sales",
        "prompt_template": (
            "You are an expert sales interviewer. "
            "Generate one realistic customer-objection scenario. "
            "Present a customer who is interested in a product but raises a specific "
            "objection such as price, competitor preference, lack of trust, or unclear ROI. "
            "Ask the candidate how they would respond and move the conversation toward "
            "a successful sale. "
            "Test consultative selling, active listening, and objection handling. "
            "Avoid generic questions."
        ),
    },
    {
        "domain": "marketing-sales",
        "prompt_template": (
            "You are an expert growth marketing interviewer. "
            "Generate one lead-conversion case study in which a company receives "
            "many leads but has a low conversion rate. "
            "Ask the candidate to identify possible causes and propose a strategy "
            "to improve conversion. "
            "The question should test funnel analysis, customer journey understanding, "
            "experimentation, and marketing-sales alignment. "
            "Make the scenario practical and non-generic."
        ),
    },
    {
        "domain": "marketing-sales",
        "prompt_template": (
            "You are a senior marketing and sales interviewer. "
            "Generate one go-to-market case-study question for launching a new product "
            "in a competitive market. "
            "Ask the candidate to explain how they would identify the target market, "
            "position the product, choose acquisition channels, define pricing, "
            "and measure launch success. "
            "The scenario should require strategic reasoning and realistic trade-offs "
            "rather than a generic marketing plan."
        ),
    },
]


# ---------------------------------------------------------------------------
# Junior System Design Prompt Templates
# ---------------------------------------------------------------------------

JUNIOR_SYSTEM_DESIGN_SCALABILITY_PROMPT = (
    "Generate one junior-level system-design interview question focused "
    "on foundational scalability. The question should ask the candidate "
    "to reason about a simple application starting with a single server "
    "and explain when and why it should move toward a multi-tier or "
    "multi-server architecture. Include basic load balancing and "
    "horizontal scaling considerations. Keep the expected architecture "
    "simple and avoid advanced distributed-system concepts."
)

JUNIOR_SYSTEM_DESIGN_DATA_PROMPT = (
    "Generate one junior-level system-design interview question focused "
    "on basic data-storage decisions. The scenario should require the "
    "candidate to choose between a relational database and a NoSQL "
    "database and explain the reasoning behind the choice. The question "
    "may also involve a basic caching layer using Redis or Memcached. "
    "Keep the scale and requirements realistic for a junior engineer "
    "and avoid advanced consistency models, distributed transactions, "
    "or multi-region database architectures."
)

JUNIOR_SYSTEM_DESIGN_API_PROMPT = (
    "Generate one junior-level system-design interview question focused "
    "on designing and protecting a simple API. The question should test "
    "fundamental API rate limiting, basic load balancing, caching, and "
    "request-handling concepts. The candidate should explain where these "
    "components fit in the architecture and what problems they solve. "
    "Keep the problem bounded and avoid advanced event-driven systems, "
    "distributed transactions, multi-region replication, or complex "
    "failure-handling strategies."
)


# ---------------------------------------------------------------------------
# Senior System Design Prompt Templates
# ---------------------------------------------------------------------------

SENIOR_SYSTEM_DESIGN_DISTRIBUTED_PROMPT = (
    "Generate one senior-level system-design interview question involving "
    "a large-scale distributed system. The question must require the "
    "candidate to analyze architectural trade-offs involving throughput, "
    "latency, availability, consistency, and partition tolerance. Include "
    "a scenario where CAP theorem considerations and failure-domain "
    "isolation matter. The candidate should justify trade-offs rather "
    "than simply name technologies."
)

SENIOR_SYSTEM_DESIGN_MULTIREGION_PROMPT = (
    "Generate one senior-level system-design interview question involving "
    "a globally distributed, multi-region system. Require the candidate "
    "to reason about cross-region replication, consistency models, "
    "regional failures, asynchronous processing, event-driven "
    "backpressure, and recovery behavior. Include competing latency, "
    "availability, correctness, and operational-cost requirements. "
    "The question should require the candidate to clarify ambiguous "
    "business requirements before finalizing the architecture."
)

SENIOR_SYSTEM_DESIGN_TRANSACTIONS_PROMPT = (
    "Generate one senior-level system-design interview question involving "
    "multiple services that must coordinate state changes reliably at "
    "large scale. Require discussion of distributed transactions, "
    "idempotency, retries, partial failures, consistency guarantees, "
    "failure-domain isolation, and asynchronous event processing. "
    "Introduce ambiguous or competing business constraints such as "
    "cost versus latency or consistency versus availability. The "
    "candidate should identify assumptions, discuss alternatives, and "
    "justify the final architecture based on explicit trade-offs."
)


# ---------------------------------------------------------------------------
# System Design Prompt Registry
# ---------------------------------------------------------------------------

SYSTEM_DESIGN_PROMPT_CONFIGS = [
    {
        "domain": "system-design",
        "seniority": "junior",
        "prompt_template": JUNIOR_SYSTEM_DESIGN_SCALABILITY_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "junior",
        "prompt_template": JUNIOR_SYSTEM_DESIGN_DATA_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "junior",
        "prompt_template": JUNIOR_SYSTEM_DESIGN_API_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "senior",
        "prompt_template": SENIOR_SYSTEM_DESIGN_DISTRIBUTED_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "senior",
        "prompt_template": SENIOR_SYSTEM_DESIGN_MULTIREGION_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "senior",
        "prompt_template": SENIOR_SYSTEM_DESIGN_TRANSACTIONS_PROMPT,
    },
]


# ---------------------------------------------------------------------------
# Product Management Prompt Templates
# ---------------------------------------------------------------------------

PRODUCT_MANAGEMENT_PROMPTS = [
    {
        "domain": "product",
        "prompt_template": (
            "A food-delivery app can build only two of these four features this quarter: "
            "faster checkout, restaurant loyalty rewards, scheduled delivery, and a "
            "personalized home feed. Prioritize the features and explain your decision. "
            "Consider user impact, business value, strategic alignment, engineering effort, "
            "and trade-offs."
        ),
        "rubric_hint": (
            "Evaluate whether the candidate clearly defines the product goal and target "
            "users, establishes prioritization criteria, compares impact against effort, "
            "makes an explicit ranking, explains trade-offs, and states key assumptions."
        ),
    },
    {
        "domain": "product",
        "prompt_template": (
            "A ride-sharing app has budget to improve only one of three areas: reducing "
            "driver cancellation, improving rider pickup accuracy, or adding a loyalty "
            "program. As the product manager, prioritize one initiative and explain how "
            "you would decide between the options."
        ),
        "rubric_hint": (
            "Evaluate problem framing, identification of affected users, prioritization "
            "criteria, expected customer and business impact, effort or feasibility "
            "considerations, trade-off reasoning, and clarity of the final recommendation."
        ),
    },
    {
        "domain": "product",
        "prompt_template": (
            "You are the product manager for a music streaming app. Monthly active users "
            "are stable, but 30-day retention has fallen from 40% to 30%. Identify the "
            "metrics you would examine to diagnose the decline and explain how each metric "
            "would help you find the underlying problem."
        ),
        "rubric_hint": (
            "Evaluate whether the candidate distinguishes the north-star metric from "
            "diagnostic metrics, considers retention cohorts and segments, identifies "
            "activation and engagement metrics, proposes meaningful breakdowns, and "
            "connects metric changes to actionable hypotheses."
        ),
    },
    {
        "domain": "product",
        "prompt_template": (
            "A mobile payments product has increased new-user sign-ups by 25%, but the "
            "percentage of users completing their first payment has decreased. As the "
            "product manager, define the key metrics and funnel stages you would analyze "
            "to understand what is happening and decide what to improve first."
        ),
        "rubric_hint": (
            "Evaluate funnel understanding, metric selection, conversion analysis, "
            "segmentation, identification of possible drop-off points, prioritization "
            "of investigation areas, and the ability to turn metrics into product actions."
        ),
    },
    {
        "domain": "product",
        "prompt_template": (
            "Estimate the number of food-delivery orders placed in a large Indian city "
            "on an average day. State your assumptions, build a simple estimation model, "
            "calculate the estimate step by step, and explain which assumptions have the "
            "largest effect on the result."
        ),
        "rubric_hint": (
            "Evaluate whether the candidate defines the scope, uses reasonable and "
            "explicit assumptions, breaks the estimate into logical components, performs "
            "consistent calculations, checks the result for plausibility, and identifies "
            "the assumptions most sensitive to the final estimate."
        ),
    },
]


# ---------------------------------------------------------------------------
# SDE Prompt Templates
# ---------------------------------------------------------------------------

SDE_PROMPT_TEMPLATES = [
    {
        "domain": "sde",
        "difficulty": "easy",
        "prompt_template": (
            "Role: Act as an experienced Software Engineering interviewer. "
            "Context: Generate one technical SDE interview question for a candidate "
            "at an easy difficulty level. Focus on fundamental programming, "
            "object-oriented programming, basic data structures, databases, "
            "debugging, or core software engineering concepts. "
            "Constraints: The question must be clear, practical, and suitable for "
            "an entry-level SDE interview. Vary the topic and question style across "
            "generations. Do not repeat or closely rephrase previously generated "
            "questions. Do not provide the answer or explanation. Return only the "
            "interview question."
        ),
    },
    {
        "domain": "sde",
        "difficulty": "medium",
        "prompt_template": (
            "Role: Act as an experienced Software Engineering interviewer. "
            "Context: Generate one technical SDE interview question for a candidate "
            "at a medium difficulty level. Focus on algorithms, data structures, "
            "database design, SQL, REST APIs, concurrency, testing, debugging, "
            "or practical software engineering problem-solving. "
            "Constraints: The question should require reasoning or application of "
            "technical concepts rather than simple recall. Vary the topic, scenario, "
            "and problem style across generations. Do not repeat or closely rephrase "
            "previously generated questions. Do not provide the answer or explanation. "
            "Return only the interview question."
        ),
    },
    {
        "domain": "sde",
        "difficulty": "hard",
        "prompt_template": (
            "Role: Act as a senior Software Engineering interviewer conducting an "
            "advanced SDE interview. Context: Generate one challenging technical "
            "question involving system design, distributed systems, scalability, "
            "performance optimization, fault tolerance, concurrency, data-intensive "
            "systems, or advanced software architecture. "
            "Constraints: The question must require multi-step technical reasoning "
            "and should reflect real-world engineering challenges. Vary the system, "
            "constraints, and problem scenario across generations. Do not repeat or "
            "closely rephrase previously generated questions. Avoid questions that "
            "can be answered with simple definitions. Do not provide the answer or "
            "explanation. Return only the interview question."
        ),
    },
]
