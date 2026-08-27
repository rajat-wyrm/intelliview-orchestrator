from workers.prompts import BEHAVIORAL_PROMPT_TEMPLATE

SAMPLE_TRANSCRIPTS = [
    {
        "scenario": "Team conflict",
        "question": "Tell me about a time you had a disagreement with a teammate.",
        "candidate_answer": (
            "I always try to communicate well with my teammates and resolve disagreements professionally."
        ),
        "expected_follow_up": True,
    },
    {
        "scenario": "Leadership",
        "question": "Tell me about a time you demonstrated leadership.",
        "candidate_answer": (
            "I am a good leader and I usually help my team whenever they have difficulties."
        ),
        "expected_follow_up": True,
    },
    {
        "scenario": "Failure",
        "question": "Tell me about a time you made a mistake.",
        "candidate_answer": (
            "Everyone makes mistakes. I learn from my mistakes and make sure I improve afterward."
        ),
        "expected_follow_up": True,
    },
    {
        "scenario": "Deadline pressure",
        "question": "Tell me about a time you worked under a difficult deadline.",
        "candidate_answer": (
            "I am comfortable working under pressure and always make sure that my work is completed on time."
        ),
        "expected_follow_up": True,
    },
    {
        "scenario": "Adaptability",
        "question": "Tell me about a time you had to adapt to an unexpected change.",
        "candidate_answer": (
            "During my second-year project, our original database service "
            "became unavailable one week before the deadline. I was responsible "
            "for the backend integration, so I evaluated two alternatives, "
            "migrated our data to the replacement service, updated the API "
            "configuration, and tested the affected endpoints with my teammate. "
            "We completed the migration two days before submission and delivered "
            "the project on time."
        ),
        "expected_follow_up": False,
    },
]


def test_behavioral_prompt_has_star_structure():
    prompt = BEHAVIORAL_PROMPT_TEMPLATE["prompt_template"]

    assert BEHAVIORAL_PROMPT_TEMPLATE["domain"] == "behavioral"
    assert "STAR" in prompt
    assert "Situation" in prompt
    assert "Task" in prompt
    assert "Action" in prompt
    assert "Result" in prompt


def test_five_sample_transcripts_cover_follow_up_cases():
    assert len(SAMPLE_TRANSCRIPTS) == 5

    follow_up_cases = [
        transcript
        for transcript in SAMPLE_TRANSCRIPTS
        if transcript["expected_follow_up"]
    ]

    complete_cases = [
        transcript
        for transcript in SAMPLE_TRANSCRIPTS
        if not transcript["expected_follow_up"]
    ]

    assert len(follow_up_cases) == 4
    assert len(complete_cases) == 1


def test_behavioral_prompt_accepts_candidate_answer():
    prompt_template = BEHAVIORAL_PROMPT_TEMPLATE["prompt_template"]

    formatted_prompt = prompt_template.format(
        candidate_answer=SAMPLE_TRANSCRIPTS[0]["candidate_answer"]
    )

    assert SAMPLE_TRANSCRIPTS[0]["candidate_answer"] in formatted_prompt
