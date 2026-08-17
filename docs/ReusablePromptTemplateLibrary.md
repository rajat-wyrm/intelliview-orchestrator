# Reusable Prompt Template Library for IntelliView Orchestrator

A standardized collection of reusable prompt templates designed for AI-powered interview workflows in the IntelliView Orchestrator.

---

# Table of Contents

1. [Introduction](#1-introduction)
2. [Objective](#2-objective)
3. [Project Scope](#3-project-scope)
4. [Workflow Identification](#4-workflow-identification)
5. [Prompt Template Design Principles](#5-prompt-template-design-principles)
6. [Standard Placeholder Definitions](#6-standard-placeholder-definitions)
7. [Reusable Prompt Template Library](#7-reusable-prompt-template-library)
   - [PT-001: Resume Analysis](#pt-001-resume-analysis)
   - [PT-002: Interview Question Generation](#pt-002-interview-question-generation)
   - [PT-003: Answer Evaluation](#pt-003-answer-evaluation)
   - [PT-004: Candidate Feedback Generation](#pt-004-candidate-feedback-generation)
   - [PT-005: Interview Report Summarization](#pt-005-interview-report-summarization)
   - [PT-006: Skill Assessment](#pt-006-skill-assessment)
8. [Prompt Library Summary](#8-prompt-library-summary)
9. [Template Testing](#9-template-testing)
10. [Usage Guidelines](#10-usage-guidelines)
11. [Best Practices](#11-best-practices)
12. [Future Improvements](#12-future-improvements)
13. [Conclusion](#13-conclusion)

---

# 1. Introduction

Artificial Intelligence (AI) has become a fundamental component of modern recruitment systems by automating repetitive tasks and assisting recruiters in making informed hiring decisions.

In AI-powered interview platforms such as **IntelliView Orchestrator**, Large Language Models (LLMs) perform several critical workflows, including:

- Resume Analysis
- Interview Question Generation
- Answer Evaluation
- Candidate Feedback Generation
- Interview Report Summarization
- Skill Assessment

As AI-assisted workflows continue to grow, writing prompts individually for every request introduces several challenges:

- Inconsistent prompt structures
- Duplicate prompt logic
- Difficult maintenance
- Variable AI responses for similar tasks

Reusable prompt templates solve these issues by providing standardized prompt structures with configurable placeholders. Instead of writing prompts repeatedly, templates accept workflow-specific information dynamically while maintaining consistency across the platform.

Benefits include:

- Improved response quality
- Consistent AI behavior
- Easier prompt maintenance
- Better scalability
- Reusability across workflows

This document presents a reusable prompt template library specifically designed for the **IntelliView Orchestrator**, supporting multiple interview workflows while remaining flexible enough for different:

- Job roles
- Experience levels
- Interview types
- Evaluation criteria

---

# 2. Objective

The primary objective of this project is to design a standardized and reusable prompt template library for IntelliView Orchestrator that improves:

- Consistency
- Maintainability
- Response quality

across AI-assisted interview workflows.

## Project Goals

- Identify common AI-driven interview workflows.
- Design reusable prompt templates for every workflow.
- Standardize prompt structures using configurable placeholders.
- Improve prompt maintainability through modular design.
- Test each template using representative sample inputs.
- Document template usage and customization.
- Provide a reusable prompt library for future IntelliView integration.

---

# 3. Project Scope

The prompt template library focuses on the primary AI workflows used by IntelliView Orchestrator.

The templates are intentionally designed to remain **LLM-independent**, allowing them to work with models such as:

- Gemini
- GPT-4o
- Grok
- Other compatible LLMs

with minimal modifications.

## Included Workflows

- Resume Analysis
- Interview Question Generation
- Answer Evaluation
- Candidate Feedback Generation
- Interview Report Summarization
- Skill Assessment

Every workflow is represented by a reusable prompt template that follows a standardized structure, allowing easy maintenance, extension, and reuse across multiple interview sessions.

---

# 4. Workflow Identification

The following AI-assisted workflows were identified as the core components of the IntelliView interview system.

| Workflow | Purpose |
|-----------|---------|
| **Resume Analysis** | Extract candidate information, identify technical and soft skills, summarize experience, and determine strengths and missing competencies. |
| **Interview Question Generation** | Generate interview questions based on the candidate profile, required skills, interview type, job role, and difficulty level. |
| **Answer Evaluation** | Evaluate candidate responses using predefined criteria and provide structured scores and feedback. |
| **Candidate Feedback Generation** | Produce constructive feedback highlighting strengths, weaknesses, and recommendations after the interview. |
| **Interview Report Summarization** | Generate a complete interview summary and hiring recommendation. |
| **Skill Assessment** | Evaluate technical and professional competencies and assign proficiency levels. |

---

# 5. Prompt Template Design Principles

Every prompt template in this library follows a standardized structure to ensure consistency and maintainability.

Each template contains the following sections.

| Component | Description |
|-----------|-------------|
| **Template ID** | Unique identifier of the prompt template |
| **Template Name** | Name of the supported workflow |
| **Objective** | Purpose of the template |
| **Workflow** | IntelliView workflow where the prompt is used |
| **Required Inputs** | Dynamic placeholders required by the template |
| **Prompt Template** | Reusable prompt containing configurable placeholders |
| **Expected Output** | Desired AI-generated response |
| **Sample Input** | Example values supplied to the template |
| **Sample Output** | Representative AI response |
| **Usage Notes** | Instructions for using the template effectively |
| **Best Practices** | Recommendations for obtaining consistent results |

---

# 6. Standard Placeholder Definitions

The reusable templates use standardized placeholders so that the same prompt can be reused across different interview scenarios.

| Placeholder | Description |
|-------------|-------------|
| `{candidate_name}` | Candidate's full name |
| `{job_role}` | Position for which the candidate is being interviewed |
| `{experience_level}` | Fresher, Junior, Mid-Level, or Senior |
| `{resume_text}` | Complete resume content |
| `{job_description}` | Job description or role requirements |
| `{skills}` | Required or extracted technical/professional skills |
| `{interview_type}` | Technical, HR, Behavioral, or Mixed interview |
| `{difficulty}` | Easy, Medium, or Hard |
| `{question}` | Interview question presented to the candidate |
| `{candidate_answer}` | Candidate's response |
| `{evaluation_criteria}` | Criteria used during evaluation |

---

# 7. Reusable Prompt Template Library

The following sections describe reusable prompt templates for each interview workflow supported by IntelliView Orchestrator.

---

## PT-001: Resume Analysis

### Template ID: **PT-001**

### Template Name: **Resume Analysis Template**

### Objective
Analyze a candidate's resume and extract structured information that can be used throughout the interview process, including interview question generation, skill assessment, and candidate evaluation.

### Workflow: **Resume Analysis**

### Purpose
This template enables the AI model to process a candidate's resume and generate a structured summary of the candidate's:
- Qualifications
- Technical competencies
- Work experience
- Educational background
- Strengths
- Potential skill gaps
The generated information is evaluated in the context of the applied job role.
---

### Required Inputs

| Input Variable | Description |
|---------------|-------------|
| `{candidate_name}` | Candidate's full name |
| `{job_role}` | Position applied for |
| `{job_description}` | Job description or role requirements |
| `{resume_text}` | Complete resume content |

---

### Reusable Prompt Template

```text
Role:
You are an experienced technical recruiter and resume analyst responsible for evaluating candidate resumes for recruitment purposes.

Task:
Analyze the provided resume and compare it with the given job role and job description.

Candidate Name:
{candidate_name}

Job Role:
{job_role}

Job Description:
{job_description}

Resume:
{resume_text}

Instructions:

1. Summarize the candidate profile.
2. Identify technical skills.
3. Identify soft skills.
4. Summarize education.
5. Summarize work experience.
6. Identify relevant projects.
7. Highlight strengths.
8. Identify missing skills compared to the job description.
9. Calculate an estimated job-role compatibility percentage.
10. Recommend whether the candidate should proceed to the interview stage.
```

---

### Expected Output

The AI should generate the following sections:

- Candidate Summary
- Technical Skills
- Soft Skills
- Education Summary
- Work Experience
- Project Summary
- Strengths
- Skill Gaps
- Job Compatibility (%)
- Interview Recommendation

---

### Sample Input

| Variable | Value |
|----------|-------|
| Candidate Name | Rahul Sharma |
| Job Role | Python Backend Developer |
| Job Description | Python, FastAPI, SQL, REST APIs, Docker |
| Resume | B.Tech CSE graduate with internships in Python development, FastAPI projects, SQL database management, and Docker deployment. |

---

### Sample Output

```text
Candidate Summary:
Rahul Sharma is a Computer Science graduate with internship experience in backend software development.

Technical Skills:
Python, FastAPI, SQL, Docker, Git

Soft Skills:
Communication, Problem Solving, Teamwork

Education:
Bachelor of Technology in Computer Science

Experience:
Python Backend Development Internship

Projects:
Inventory Management API
Task Management System

Strengths:
Strong Python fundamentals
Experience with REST APIs
Hands-on backend development

Skill Gaps:
Limited cloud deployment experience
No CI/CD exposure

Job Compatibility:
88%

Recommendation:
Proceed to Technical Interview
```

---

### Usage Notes

- Use before interview scheduling.
- Suitable for technical and HR interviews.
- Can personalize interview questions.
- Can support automated resume screening.

---

### Best Practices

- Provide the complete resume text.
- Include the complete job description.
- Avoid abbreviating technical skills.
- Maintain consistent formatting across resumes.

---

# PT-002: Interview Question Generation

### Template ID: **PT-002**

### Template Name: **Interview Question Generation Template**

### Objective
Generate structured interview questions tailored to the candidate's profile, job role, interview type, required skills, and desired difficulty level.

### Workflow: **Interview Question Generation**

### Purpose
This template generates relevant interview questions by considering the candidate's resume, required technical skills, interview type, experience level, and job requirements. It also produces expected answers and follow-up questions to assist interviewers during the interview process.

---

### Required Inputs

| Input Variable | Description |
|----------------|-------------|
| `{job_role}` | Position being interviewed |
| `{skills}` | Required technical skills |
| `{experience_level}` | Fresher, Junior, Mid-Level, Senior |
| `{interview_type}` | Technical, HR, Behavioral |
| `{difficulty}` | Easy, Medium, Hard |

---

### Reusable Prompt Template

```text
Role:
You are an experienced technical interviewer.

Task:
Generate interview questions appropriate for the candidate profile.

Job Role:
{job_role}

Skills:
{skills}

Experience Level:
{experience_level}

Interview Type:
{interview_type}

Difficulty:
{difficulty}

Instructions:

1. Generate five interview questions.
2. Arrange the questions from easier to harder.
3. For each question provide:
   - Purpose
   - Expected Answer
   - Difficulty
   - Follow-up Question
4. Avoid repeated questions.
5. Ensure the questions match the required skills.
```

---

### Expected Output

For every generated question provide:

- Question
- Purpose
- Expected Answer
- Difficulty
- Follow-up Question

---

### Sample Input

| Variable | Value |
|----------|-------|
| Job Role | Python Backend Developer |
| Skills | Python, FastAPI, SQL, Docker |
| Experience Level | Fresher |
| Interview Type | Technical |
| Difficulty | Medium |

---

### Sample Output

```text
Question 1:
Explain the difference between a list and a tuple in Python.

Purpose:
Evaluate Python fundamentals.

Expected Answer:
Lists are mutable whereas tuples are immutable.

Difficulty:
Easy

Follow-up Question:
When would you choose a tuple instead of a list?
```

---

### Usage Notes

- Can be used before every interview round.
- Supports multiple interview types.
- Suitable for adaptive interview systems.

---

### Best Practices

- Provide accurate candidate skill information.
- Match the difficulty level to candidate experience.
- Avoid overly broad skill lists.
- Update required skills according to the job description.

---

# PT-003: Answer Evaluation

### Template ID: **PT-003**

### Template Name: **Answer Evaluation Template**

### Objective
Evaluate a candidate's interview response using predefined evaluation criteria and generate a structured assessment that includes scores, strengths, weaknesses, and improvement suggestions.

### Workflow: **Answer Evaluation**

### Purpose

This template enables the AI model to objectively evaluate candidate responses by assessing:

- Technical correctness
- Conceptual understanding
- Communication clarity
- Problem-solving ability
- Overall relevance to the interview question

---

### Required Inputs

| Input Variable | Description |
|----------------|-------------|
| `{question}` | Interview question asked to the candidate |
| `{candidate_answer}` | Candidate's response |
| `{evaluation_criteria}` | Evaluation criteria |
| `{job_role}` | Position applied for |
| `{difficulty}` | Difficulty level of the question |

---

### Reusable Prompt Template

```text
Role:
You are an experienced technical interviewer responsible for evaluating interview responses objectively.

Task:
Evaluate the candidate's answer based on the provided interview question and evaluation criteria.

Question:
{question}

Candidate Answer:
{candidate_answer}

Evaluation Criteria:
{evaluation_criteria}

Job Role:
{job_role}

Difficulty:
{difficulty}

Instructions:

1. Evaluate the answer objectively.
2. Do not assume knowledge that is not present in the answer.
3. Reward partially correct answers where appropriate.
4. Provide constructive feedback.
5. Assign a score out of 10.
6. Return ONLY valid JSON.
```

---

### Expected Output

```json
{
  "score": 8,
  "technical_accuracy": "High",
  "communication": "Good",
  "problem_solving": "Moderate",
  "strengths": [],
  "weaknesses": [],
  "improvement_suggestions": [],
  "overall_feedback": "",
  "recommendation": ""
}
```

---

### Sample Input

| Variable | Value |
|----------|-------|
| Question | Explain the difference between multithreading and multiprocessing. |
| Candidate Answer | Multithreading allows multiple threads inside one process while multiprocessing creates separate processes. |
| Evaluation Criteria | Accuracy, Clarity, Examples, Communication |
| Job Role | Python Backend Developer |
| Difficulty | Medium |

---

### Sample Output

```json
{
  "score": 9,
  "technical_accuracy": "High",
  "communication": "Excellent",
  "problem_solving": "Good",
  "strengths": [
    "Correct conceptual explanation",
    "Clear communication"
  ],
  "weaknesses": [
    "Could include practical examples"
  ],
  "improvement_suggestions": [
    "Discuss Python GIL",
    "Mention use cases"
  ],
  "overall_feedback": "Strong understanding of the concept with minor scope for improvement.",
  "recommendation": "Proceed to next question"
}
```

---

### Usage Notes

- Used immediately after every candidate response.
- Suitable for technical, HR, and behavioral interviews.
- Supports automated scoring pipelines.

---

### Best Practices

- Keep evaluation criteria consistent across interviews.
- Evaluate only the provided answer.
- Encourage constructive rather than punitive feedback.
- Store JSON responses for downstream analytics.

---

# PT-004: Candidate Feedback Generation

### Template ID: **PT-004**

### Template Name: **Candidate Feedback Generation Template**

### Objective
Generate personalized, constructive, and actionable feedback based on the candidate's overall interview performance.

### Workflow: **Candidate Feedback Generation**

### Purpose
This template summarizes interview performance by identifying:

- Strengths
- Weaknesses
- Learning opportunities
- Actionable recommendations

that help candidates improve for future interviews.

---

### Required Inputs

| Input Variable | Description |
|----------------|-------------|
| `{candidate_name}` | Candidate's full name |
| `{evaluation_results}` | Consolidated interview evaluation results |
| `{job_role}` | Position applied for |

---

### Reusable Prompt Template

```text
Role:
You are an experienced interview coach providing constructive candidate feedback.

Task:
Generate professional post-interview feedback.

Candidate:
{candidate_name}

Job Role:
{job_role}

Evaluation Summary:
{evaluation_results}

Instructions:

1. Be constructive and encouraging.
2. Highlight strengths.
3. Explain improvement areas.
4. Suggest learning resources or focus areas.
5. Return ONLY valid JSON.
```

---

### Expected Output

```json
{
  "overall_performance": "",
  "strengths": [],
  "areas_for_improvement": [],
  "recommended_learning": [],
  "final_feedback": ""
}
```

---

### Sample Output

```json
{
  "overall_performance": "Good",
  "strengths": [
    "Strong Python fundamentals",
    "Good communication",
    "Logical problem solving"
  ],
  "areas_for_improvement": [
    "Database optimization",
    "System design concepts"
  ],
  "recommended_learning": [
    "Practice SQL optimization",
    "Study REST API architecture",
    "Learn Docker deployment"
  ],
  "final_feedback": "You demonstrated a solid technical foundation. Improving database optimization and system design knowledge will further strengthen your interview performance."
}
```

---

### Usage Notes

- Used after the interview concludes.
- Can be shared directly with candidates.
- Supports personalized learning recommendations.

---

### Best Practices

- Maintain a positive and professional tone.
- Base feedback only on interview evidence.
- Provide specific and actionable suggestions.

---

# PT-005: Interview Report Summarization

### Template ID: **PT-005**

### Template Name: **Interview Report Summarization Template**

### Objective
Generate a comprehensive interview report summarizing the candidate's overall interview performance, technical competency, communication skills, behavioral observations, and hiring recommendation.

### Workflow: **Interview Report Summarization**

### Purpose

This template consolidates information collected throughout the interview process into a structured report for recruiters, hiring managers, and interview panels.

---

### Required Inputs

| Input Variable | Description |
|----------------|-------------|
| `{candidate_name}` | Candidate's full name |
| `{job_role}` | Position applied for |
| `{question_summary}` | List of interview questions asked |
| `{evaluation_results}` | Consolidated evaluation results |
| `{overall_score}` | Final interview score |

---

### Reusable Prompt Template

```text
Role:
You are an experienced hiring manager responsible for preparing final interview reports.

Task:
Generate a professional interview summary report.

Candidate Name:
{candidate_name}

Job Role:
{job_role}

Questions Asked:
{question_summary}

Evaluation Summary:
{evaluation_results}

Overall Score:
{overall_score}

Instructions:

1. Summarize the interview objectively.
2. Highlight technical strengths.
3. Highlight communication strengths.
4. Mention improvement areas.
5. Provide an overall recommendation.
6. Return ONLY valid JSON.
```

---

### Expected Output

```json
{
  "candidate_name": "",
  "job_role": "",
  "overall_score": 0,
  "technical_performance": "",
  "communication": "",
  "behavioral_assessment": "",
  "strengths": [],
  "areas_for_improvement": [],
  "overall_summary": "",
  "hiring_recommendation": ""
}
```

---

### Sample Output

```json
{
  "candidate_name": "Rahul Sharma",
  "job_role": "Python Backend Developer",
  "overall_score": 86,
  "technical_performance": "Strong",
  "communication": "Very Good",
  "behavioral_assessment": "Positive and collaborative",
  "strengths": [
    "Python programming",
    "REST API development",
    "Logical reasoning"
  ],
  "areas_for_improvement": [
    "Cloud deployment",
    "CI/CD pipelines"
  ],
  "overall_summary": "The candidate demonstrated strong backend development knowledge with good communication skills. Minor improvements in deployment technologies would further strengthen the profile.",
  "hiring_recommendation": "Recommended for the next recruitment stage."
}
```

---

### Usage Notes

- Used after completion of the interview.
- Supports recruiter decision-making.
- Can be stored in the candidate database.
- Useful for future interview comparisons and audits.

---

### Best Practices

- Include evaluation data from all interview rounds.
- Avoid subjective statements.
- Ensure recommendations are evidence-based.

---

# PT-006: Skill Assessment

### Template ID: **PT-006**

### Template Name: **Skill Assessment Template**

### Objective
Evaluate the candidate's proficiency across required technical and professional skills based on interview responses and assign competency levels.

### Workflow: **Skill Assessment**

### Purpose
This template evaluates demonstrated competency levels, identifies strengths and weaknesses, and recommends learning paths where required.

---

### Required Inputs

| Input Variable | Description |
|----------------|-------------|
| `{candidate_name}` | Candidate's full name |
| `{job_role}` | Position applied for |
| `{required_skills}` | Skills required for the role |
| `{candidate_answers}` | Candidate interview responses |
| `{evaluation_results}` | Interview evaluation summary |

---

### Reusable Prompt Template

```text
Role:
You are an experienced technical assessor.

Task:
Assess the candidate's proficiency across the required skills based on interview responses.

Candidate Name:
{candidate_name}

Job Role:
{job_role}

Required Skills:
{required_skills}

Candidate Responses:
{candidate_answers}

Evaluation Summary:
{evaluation_results}

Instructions:

1. Evaluate each required skill independently.
2. Assign a proficiency level.
3. Justify every assessment.
4. Recommend learning areas where necessary.
5. Return ONLY valid JSON.
```

---

### Expected Output

```json
{
  "candidate_name": "",
  "job_role": "",
  "skill_assessment": [
    {
      "skill": "",
      "proficiency": "",
      "score": 0,
      "remarks": ""
    }
  ],
  "overall_skill_rating": "",
  "recommended_learning": []
}
```

---

### Sample Output

```json
{
  "candidate_name": "Rahul Sharma",
  "job_role": "Python Backend Developer",
  "skill_assessment": [
    {
      "skill": "Python",
      "proficiency": "Advanced",
      "score": 9,
      "remarks": "Excellent understanding of Python fundamentals."
    },
    {
      "skill": "FastAPI",
      "proficiency": "Intermediate",
      "score": 8,
      "remarks": "Good understanding of API development."
    },
    {
      "skill": "SQL",
      "proficiency": "Intermediate",
      "score": 7,
      "remarks": "Needs more optimization knowledge."
    },
    {
      "skill": "Docker",
      "proficiency": "Beginner",
      "score": 5,
      "remarks": "Basic knowledge demonstrated."
    }
  ],
  "overall_skill_rating": "Intermediate",
  "recommended_learning": [
    "Docker",
    "CI/CD",
    "Cloud Deployment"
  ]
}
```

---

### Usage Notes

- Used after answer evaluation.
- Supports hiring decisions.
- Can generate skill dashboards.
- Useful for candidate performance analytics.

---

### Best Practices

- Assess only demonstrated skills.
- Avoid assumptions based on resumes.
- Keep proficiency levels consistent.
- Update required skills according to job descriptions.

---

# 8. Prompt Library Summary

| Template ID | Template Name | Workflow | Output Format |
|-------------|---------------|----------|---------------|
| PT-001 | Resume Analysis | Resume Analysis | Structured Sections |
| PT-002 | Interview Question Generation | Question Generation | Structured Sections |
| PT-003 | Answer Evaluation | Answer Evaluation | JSON |
| PT-004 | Candidate Feedback Generation | Feedback Generation | JSON |
| PT-005 | Interview Report Summarization | Report Generation | JSON |
| PT-006 | Skill Assessment | Skill Assessment | JSON |

---

# 9. Template Testing

## 9.1 Testing Objective

The prompt templates were tested to ensure they consistently generate relevant, structured, and accurate responses across different interview workflows.

The testing process verifies:

- Correctness
- Completeness
- Response structure
- Consistency
- Relevance

---

## 9.2 Testing Methodology

1. Define representative sample inputs.
2. Populate template placeholders.
3. Execute the prompt using an LLM.
4. Compare the generated response with the expected format.
5. Evaluate quality metrics.
6. Record observations and improvements.

---

## 9.3 Evaluation Criteria

| Metric | Description |
|---------|-------------|
| Accuracy | Correctness of generated response |
| Relevance | Suitability for the workflow |
| Completeness | Coverage of requested information |
| Clarity | Ease of understanding |
| Consistency | Uniformity across executions |
| Output Structure | Adherence to required format |

---

## 9.4 Test Results

| Template | Accuracy | Relevance | Clarity | Structure | Result |
|----------|----------|-----------|----------|-----------|--------|
| PT-001 | Excellent | Excellent | Excellent | Excellent | Passed |
| PT-002 | Excellent | Excellent | Excellent | Excellent | Passed |
| PT-003 | Excellent | Excellent | Very Good | Excellent | Passed |
| PT-004 | Very Good | Excellent | Excellent | Excellent | Passed |
| PT-005 | Excellent | Excellent | Excellent | Excellent | Passed |
| PT-006 | Excellent | Excellent | Very Good | Excellent | Passed |

---

## 9.5 Testing Observations

Testing demonstrated that all prompt templates consistently generated structured and relevant responses.

The JSON-based templates integrate well with backend systems by simplifying parsing and reducing post-processing.

Overall, the prompt library achieved its goals of:

- Consistency
- Maintainability
- Response quality
- Adaptability

---

# 10. Usage Guidelines

1. Select the appropriate prompt template.
2. Replace placeholders with actual values.
3. Verify input completeness.
4. Submit the prompt to the chosen AI model.
5. Review generated responses.
6. Store or process outputs as required.

## Placeholder Examples

| Placeholder | Example |
|-------------|---------|
| `{candidate_name}` | Rahul Sharma |
| `{job_role}` | Python Backend Developer |
| `{experience_level}` | Fresher |
| `{resume_text}` | Candidate Resume |
| `{job_description}` | Backend Developer Job Description |
| `{skills}` | Python, FastAPI, SQL |
| `{question}` | Explain REST APIs. |
| `{candidate_answer}` | Candidate Response |
| `{evaluation_criteria}` | Accuracy, Clarity, Problem Solving |

---

# 11. Best Practices

- Clearly define the AI's role.
- Provide sufficient context.
- Use standardized placeholders.
- Populate all required variables.
- Prefer structured outputs.
- Avoid ambiguous instructions.
- Keep templates modular.
- Validate AI-generated responses.
- Review templates periodically.
- Test with diverse candidate profiles.

---

# 12. Future Improvements

Potential future enhancements include:

- Multilingual interview support
- Adaptive prompts based on candidate performance
- Retrieval-Augmented Generation (RAG) integration
- Automated prompt optimization
- Version-controlled prompt repositories
- Coding assessment support
- Personalized prompts using interview history
- Analytics dashboards for prompt effectiveness

---

# 13. Conclusion

This project introduced a reusable prompt template library for IntelliView Orchestrator covering six core interview workflows:

- Resume Analysis
- Interview Question Generation
- Answer Evaluation
- Candidate Feedback Generation
- Interview Report Summarization
- Skill Assessment

The standardized templates improve consistency, maintainability, and response quality while remaining flexible across AI models. The resulting prompt library provides a scalable foundation for future enhancements and supports reliable AI-assisted interview orchestration.

