import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db import Base
from database.models import (
    Candidate,
    InterviewSession,
    InterviewTemplate,
    Question,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_create_candidate(db_session):
    candidate = Candidate(candidate_id="c1", name="Bhawna", email="bhawna@example.com")

    db_session.add(candidate)
    db_session.commit()

    saved = db_session.query(Candidate).filter_by(candidate_id="c1").first()

    assert saved is not None
    assert saved.name == "Bhawna"
    assert saved.email == "bhawna@example.com"


def test_create_interview_session(db_session):
    session = InterviewSession(session_id="s1", candidate_id="c1", status="pending")

    db_session.add(session)
    db_session.commit()

    saved = db_session.query(InterviewSession).filter_by(session_id="s1").first()

    assert saved is not None
    assert saved.candidate_id == "c1"
    assert saved.status == "pending"


def test_create_question(db_session):
    question = Question(question_id="q1", text="What is Python?", category="Python", difficulty="easy")

    db_session.add(question)
    db_session.commit()

    saved = db_session.query(Question).filter_by(question_id="q1").first()

    assert saved is not None
    assert saved.category == "Python"
    assert saved.difficulty == "easy"


def test_create_interview_template(db_session):
    template = InterviewTemplate(template_id="t1", name="Python Interview", interview_type="technical")

    db_session.add(template)
    db_session.commit()

    saved = db_session.query(InterviewTemplate).filter_by(template_id="t1").first()

    assert saved is not None
    assert saved.name == "Python Interview"
    assert saved.interview_type == "technical"


def test_candidate_repr():
    candidate = Candidate(
        candidate_id="c1",
        name="Bhawna",
        email="bhawna@example.com",
    )

    assert "Candidate" in repr(candidate)
    assert "Bhawna" in repr(candidate)


def test_question_repr():
    question = Question(
        question_id="q1",
        text="What is Python?",
        category="Python",
        difficulty="easy",
    )

    assert "Question" in repr(question)
    assert "Python" in repr(question)


def test_interview_template_repr():
    template = InterviewTemplate(
        template_id="t1",
        name="Python Interview",
        interview_type="technical",
    )

    assert "InterviewTemplate" in repr(template)
    assert "Python Interview" in repr(template)


def test_interview_session_repr():
    session = InterviewSession(
        session_id="s1",
        candidate_id="c1",
        status="pending",
    )

    assert "InterviewSession" in repr(session)
    assert "pending" in repr(session)
