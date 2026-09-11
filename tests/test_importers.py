from pathlib import Path

import pytest

from quiz_platform.question_bank import (
    CsvQuestionImportService,
    CsvQuestionImporter,
    JsonLinesQuestionImportService,
    JsonLinesQuestionImporter,
    JsonQuestionImportService,
    JsonQuestionImporter,
    QuestionImporter,
    import_questions,
    register_import_service,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.mark.parametrize(
    ("creator_type", "product_type"),
    [
        (JsonQuestionImportService, JsonQuestionImporter),
        (CsvQuestionImportService, CsvQuestionImporter),
        (JsonLinesQuestionImportService, JsonLinesQuestionImporter),
    ],
)
def test_each_concrete_creator_returns_its_product(creator_type, product_type):
    product = creator_type().create_importer()

    assert isinstance(product, QuestionImporter)
    assert type(product) is product_type


def test_json_and_csv_imports_have_fixed_accepted_ids():
    json_questions, json_report = import_questions(str(DATA_DIR / "questions.json"))
    csv_questions, csv_report = import_questions(str(DATA_DIR / "questions.csv"))

    assert [question["id"] for question in json_questions] == [
        "Q-1001",
        "Q-1002",
        "Q-1003",
        "Q-1004",
        "Q-1005",
        "Q-1006",
        "Q-1007",
        "Q-1008",
    ]
    assert json_report["accepted"] == 8
    assert [question["id"] for question in csv_questions] == ["Q-2001", "Q-2002", "Q-2003"]
    assert csv_report["accepted"] == 3


def test_factory_method_imports_json_lines_through_creator_and_facade():
    service = JsonLinesQuestionImportService()

    questions, report = service.import_questions(str(DATA_DIR / "questions.jsonl"))
    facade_questions, _facade_report = import_questions(str(DATA_DIR / "questions.jsonl"))

    assert [question["id"] for question in questions] == ["Q-3001", "Q-3002", "Q-3003"]
    assert [question["id"] for question in facade_questions] == [
        "Q-3001",
        "Q-3002",
        "Q-3003",
    ]
    assert report["loaded"] == 3
    assert report["accepted"] == 3


def test_json_lines_requires_an_object_per_non_empty_line(tmp_path):
    malformed = tmp_path / "questions.jsonl"
    malformed.write_text('["not", "an", "object"]\n', encoding="utf-8")

    with pytest.raises(ValueError):
        import_questions(str(malformed))


def test_csv_missing_required_header_raises_value_error(tmp_path):
    malformed = tmp_path / "questions.csv"
    malformed.write_text("id,text\nQ-1,Incomplete\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        import_questions(str(malformed))


def test_registered_creator_uses_shared_result_validation():
    class BrokenReportImporter(QuestionImporter):
        def import_file(self, path):
            del path
            return [{"id": "Q-X"}], {
                "loaded": 1,
                "accepted": 0,
                "rejected": 1,
                "duplicate_warnings": [],
                "errors": [{}],
            }

    @register_import_service(".broken-report")
    class BrokenReportService(JsonQuestionImportService):
        def create_importer(self):
            return BrokenReportImporter()

    with pytest.raises(ValueError, match="accepted count"):
        import_questions("questions.broken-report")
