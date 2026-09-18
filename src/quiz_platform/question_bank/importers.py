"""Question importer Products and Factory Method Creators."""

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path

from quiz_platform.question_bank.core import (
    empty_import_report,
    find_duplicates,
    load_question_file,
    normalise_question,
    split_valid_records,
)

CSV_REQUIRED_FIELDS = {
    "id",
    "text",
    "format",
    "topic",
    "difficulty",
    "learning_outcomes",
    "status",
    "estimated_minutes",
    "tags",
    "last_used",
}

_IMPORT_SERVICE_TYPES = {}


def register_import_service(suffix: str):
    """Register a Concrete Creator for a file suffix."""
    normalised_suffix = suffix.lower()
    if not normalised_suffix.startswith("."):
        raise ValueError("an importer suffix must start with '.'")

    def register(service_type):
        if normalised_suffix in _IMPORT_SERVICE_TYPES:
            raise ValueError(f"duplicate importer suffix: {normalised_suffix}")
        _IMPORT_SERVICE_TYPES[normalised_suffix] = service_type
        return service_type

    return register


class QuestionImporter(ABC):
    """Product interface for importing one supported question format."""

    @abstractmethod
    def import_file(self, path: str) -> tuple[list[dict], dict]:
        """Load one file and return accepted questions plus an import report."""


class JsonQuestionImporter(QuestionImporter):
    """Concrete Product for JSON arrays."""

    def import_file(self, path: str) -> tuple[list[dict], dict]:
        return _complete_import(load_question_file(path))


class CsvQuestionImporter(QuestionImporter):
    """Concrete Product for CSV rows."""

    def import_file(self, path: str) -> tuple[list[dict], dict]:
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            missing = sorted(CSV_REQUIRED_FIELDS - fieldnames)
            if missing:
                raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
            records = []
            for row in reader:
                record = dict(row)
                record["learning_outcomes"] = _split_csv_list(record["learning_outcomes"])
                record["tags"] = _split_csv_list(record["tags"])
                record["last_used"] = record["last_used"].strip() or None
                records.append(record)
        return _complete_import(records)


class JsonLinesQuestionImporter(QuestionImporter):
    """Concrete Product for one JSON question object per non-empty line."""

    def import_file(self, path: str) -> tuple[list[dict], dict]:
        # ??? TODO fill in
        with open (path, encoding="utf-8") as handle:
            records = []
            for line in handle:
                line = line.strip()
                if not line:
                    continue

                # raise NotImplementedError("??? TODO fill in")
                raise NotImplementedError("The JSON Lines import has not been implemented yet!")
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"invalid JSON on line {len(records) + 1}: {error}") from error
                records.append(record)
        return _complete_import(records)
        

class QuestionImportService(ABC):
    """Creator with a stable import-and-validation workflow."""

    def import_questions(self, path: str) -> tuple[list[dict], dict]:
        """Create a Product, import records, then validate the result contract."""
        # ??? TODO obtain the Product through the Factory Method
        importer = self.create_importer()
        questions, report = importer.import_file(path)
        _validate_import_result(questions, report)
        return questions, report

    @abstractmethod
    def create_importer(self) -> QuestionImporter:
        """Factory Method returning the Product used by this Creator."""


@register_import_service(".json")
class JsonQuestionImportService(QuestionImportService):
    """Concrete Creator for JSON array imports."""

    def create_importer(self) -> QuestionImporter:
        # ??? TODO fill in
        for suffix, service_type in _IMPORT_SERVICE_TYPES.items():
            if suffix == ".json":
                return service_type()
        # raise NotImplementedError("??? TODO fill in")
        raise NotImplementedError("The JSON import service has not been implemented yet!")



@register_import_service(".csv")
class CsvQuestionImportService(QuestionImportService):
    """Concrete Creator for CSV imports."""

    def create_importer(self) -> QuestionImporter:
        # ??? TODO fill in
        for suffix, service_type in _IMPORT_SERVICE_TYPES.items():
            if suffix == ".csv":
                return service_type()
        
        # raise NotImplementedError("??? TODO fill in")
        raise NotImplementedError("The CSV import service has not been implemented yet!")
        

@register_import_service(".jsonl")
class JsonLinesQuestionImportService(QuestionImportService):
    """Concrete Creator for JSON Lines imports."""

    def create_importer(self) -> QuestionImporter:
        # ??? TODO fill in
        # raise NotImplementedError("??? TODO fill in")
        for suffix, service_type in _IMPORT_SERVICE_TYPES.items():
            if suffix == ".jsonl":
                return service_type()
        raise NotImplementedError("The JSON Lines import service has not been implemented yet!")


def _complete_import(raw_records: list[dict]) -> tuple[list[dict], dict]:
    """Apply the common domain processing after format-specific loading."""
    report = empty_import_report()
    report["loaded"] = len(raw_records)
    normalised = [normalise_question(record) for record in raw_records]
    accepted, rejected = split_valid_records(normalised)
    report["accepted"] = len(accepted)
    report["rejected"] = len(rejected)
    report["errors"] = rejected
    report["duplicate_warnings"] = find_duplicates(accepted)
    return accepted, report


def _split_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def _validate_import_result(questions: list[dict], report: dict) -> None:
    """Validate the contract shared by every Product result."""
    required_keys = {
        "loaded",
        "accepted",
        "rejected",
        "duplicate_warnings",
        "errors",
    }
    missing = sorted(required_keys - set(report))
    if missing:
        raise ValueError(f"import report missing keys: {', '.join(missing)}")
    if report["accepted"] != len(questions):
        raise ValueError("accepted count does not match imported questions")
    if report["loaded"] != report["accepted"] + report["rejected"]:
        raise ValueError("loaded count must equal accepted plus rejected")
    if report["rejected"] != len(report["errors"]):
        raise ValueError("rejected count does not match error entries")


def import_questions(path: str) -> tuple[list[dict], dict]:
    """Select a registered Creator and run its stable operation."""
    suffix = Path(path).suffix.lower()
    service_type = _IMPORT_SERVICE_TYPES.get(suffix)
    if service_type is None:
        raise ValueError(f"unsupported question file extension: {suffix or '(none)'}")
    return service_type().import_questions(path)
