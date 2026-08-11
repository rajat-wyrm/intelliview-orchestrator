"""
Resume Parser

Extracts text and basic candidate information from PDF resumes.

Extracted information:
- Full resume text
- Technical skills
- Education
- Work experience in years
"""

import re

from pypdf import PdfReader


# Skills that the parser knows how to detect.
# This list can be expanded as the project grows.
KNOWN_SKILLS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "C++",
    "C",
    "SQL",
    "HTML",
    "CSS",
    "React",
    "Node.js",
    "FastAPI",
    "Django",
    "Spring Boot",
    "AWS",
    "Azure",
    "Docker",
    "Kubernetes",
    "Git",
    "GitHub",
    "Machine Learning",
    "Deep Learning",
    "TensorFlow",
    "PyTorch",
    "MongoDB",
    "PostgreSQL",
    "MySQL",
    "Redis",
    "Linux",
]


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from all pages of a PDF.

    Args:
        pdf_path: Path to the resume PDF.

    Returns:
        Extracted text as a single string.

    Raises:
        ValueError: If the PDF does not contain extractable text.
    """

    reader = PdfReader(pdf_path)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    resume_text = "\n".join(pages).strip()

    if not resume_text:
        raise ValueError("Could not extract text from the PDF")

    return resume_text


def extract_skills(text: str) -> list[str]:
    """
    Extract known technical skills from resume text.

    Matching is case-insensitive.

    Args:
        text: Extracted resume text.

    Returns:
        List of detected skills.
    """

    found_skills = []

    for skill in KNOWN_SKILLS:
        # Escape special characters such as + and .
        escaped_skill = re.escape(skill)

        # Match the skill as a separate term rather than
        # matching it inside another word.
        pattern = rf"(?<!\w){escaped_skill}(?!\w)"

        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)

    return found_skills


def extract_experience_years(text: str) -> float | None:
    """
    Extract explicitly stated years of professional experience.

    Examples detected:
        "2 years of experience"
        "3+ years experience"
        "5 years of professional experience"
        "Experience: 4 years"

    Args:
        text: Extracted resume text.

    Returns:
        Number of years of experience, or None if not found.
    """

    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s+years?\s+(?:of\s+)?(?:professional\s+)?experience",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\+?\s*years?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return float(match.group(1))

    return None


def extract_education(text: str) -> list[str]:
    """
    Extract education-related lines from resume text.

    This uses simple keyword matching rather than a heavy NLP model.

    Args:
        text: Extracted resume text.

    Returns:
        List of education-related lines.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    education_keywords = [
        "education",
        "academic",
        "qualification",
        "qualifications",
        "university",
        "college",
        "b.tech",
        "btech",
        "m.tech",
        "mtech",
        "bachelor",
        "master",
        "phd",
        "degree",
    ]

    education = []

    for line in lines:
        line_lower = line.lower()

        if any(keyword in line_lower for keyword in education_keywords):
            education.append(line)

    return education


def parse_resume(pdf_path: str) -> dict:
    """
    Parse a resume PDF and extract candidate information.

    Args:
        pdf_path: Path to the resume PDF.

    Returns:
        Dictionary containing:
            - resume_text
            - skills
            - education
            - experience_years
    """

    resume_text = extract_text_from_pdf(pdf_path)

    return {
        # Candidate.resume_text currently has a database
        # limit of 10,000 characters.
        "resume_text": resume_text[:10000],
        "skills": extract_skills(resume_text),
        "education": extract_education(resume_text),
        "experience_years": extract_experience_years(resume_text),
    }