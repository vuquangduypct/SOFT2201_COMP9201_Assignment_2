from pathlib import Path

from quiz_platform.question_bank.core import build_candidate_pool
from quiz_platform.question_bank.importers import (
    CsvQuestionImporter,
    JsonQuestionImporter,
    import_questions,
    importer_for_path,
)
from quiz_platform.question_bank.session import QuestionBankSession


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _questions():
    return [
        {
            "id": "Q-1",
            "status": "draft",
            "topic": "testing",
            "format": "short_answer",
            "difficulty": 1,
        },
        {
            "id": "Q-2",
            "status": "approved",
            "topic": "design",
            "format": "code_reading",
            "difficulty": 2,
        },
    ]


def test_json_and_csv_imports_have_the_existing_report_shape():
    json_questions, json_report = import_questions(str(DATA_DIR / "questions.json"))
    csv_questions, csv_report = import_questions(str(DATA_DIR / "questions.csv"))

    assert len(json_questions) == 8
    assert json_report["accepted"] == 8
    assert len(csv_questions) == 3
    assert csv_report["accepted"] == 3


def test_legacy_client_directly_constructs_products():
    assert isinstance(importer_for_path("questions.json"), JsonQuestionImporter)
    assert isinstance(importer_for_path("questions.csv"), CsvQuestionImporter)


def test_candidate_pool_uses_ordered_first_failure():
    questions = _questions()
    candidates, report = build_candidate_pool(
        questions,
        {"required_status": "approved", "topics": ["testing"]},
    )

    assert candidates == []
    assert report["excluded_by_status"] == ["Q-1"]
    assert report["excluded_by_topic"] == ["Q-2"]


def test_direct_moderation_and_conditional_undo_restore_exact_state():
    session = QuestionBankSession(_questions())

    session.retire_question("Q-1")
    session.approve_question("Q-1")

    assert session.status_of("Q-1") == "approved"
    assert session.undo_last() is True
    assert session.status_of("Q-1") == "retired"
    assert session.undo_last() is True
    assert session.status_of("Q-1") == "draft"
    assert session.undo_last() is False
