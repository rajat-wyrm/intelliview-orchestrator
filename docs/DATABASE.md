# Database Documentation

## Overview

The IntelliView Orchestrator uses PostgreSQL as its primary database with SQLAlchemy ORM for database operations.

The database stores interview sessions, candidate information, question banks, interview templates, and AI evaluation results.

---

## Database Tables

### InterviewSession

Stores information about every interview session.

| Field | Description |

|-------|-------------|

| session_id | Unique interview session ID |

| candidate_id | Candidate identifier |

| status | Interview status |

| assigned_node | Worker handling the interview |

| start_time | Interview start time |

| end_time | Interview end time |

| risk_score | AI-generated risk score |

| video_analysis | Video analysis result |

| audio_analysis | Audio analysis result |

| evaluation_analysis | Overall AI evaluation |

| overall_score | Final interview score |

---

### Question

Stores interview questions.

| Field | Description |

|-------|-------------|

| question_id | Unique question ID |

| text | Interview question |

| category | Question category |

| difficulty | Difficulty level |

| tags | Related tags |

| usage_count | Number of times used |

| avg_score | Average candidate score |

---

### Candidate

Stores candidate profiles.

| Field | Description |

|-------|-------------|

| candidate_id | Candidate ID |

| name | Candidate name |

| email | Email address |

| resume_text | Resume content |

| skills | Skill set |

| interview_history | Previous interviews |

| avg_score | Average interview score |

| total_interviews | Total interviews completed |

---

### InterviewTemplate

Stores interview templates.

| Field | Description |

|-------|-------------|

| template_id | Template ID |

| name | Template name |

| interview_type | Interview type |

| duration_minutes | Interview duration |

| question_count | Number of questions |

| category_distribution | Category-wise distribution |

| difficulty_distribution | Difficulty distribution |

| usage_count | Number of times used |

| success_rate | Template success rate |

---

## ORM

The project uses SQLAlchemy ORM.

Database connection is managed using:

- SQLAlchemy Engine

- SessionLocal

- Declarative Base

---

## Database Workflow

1. Candidate starts interview.

2. Session is created.

3. Candidate information is stored.

4. Questions are fetched.

5. AI evaluation results are saved.

6. Final scores are stored for reporting.

---

## Technologies

- PostgreSQL

- SQLAlchemy ORM

- Python

- FastAPI
