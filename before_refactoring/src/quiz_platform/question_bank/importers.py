"""Legacy importers selected and constructed directly by the client boundary."""

import csv
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


class QuestionImporter(ABC):
    """Interface shared by the format-specific importers."""

    @abstractmethod
    def import_file(self, path: str) -> tuple[list[dict], dict]:
        """Load one file and return accepted questions plus a report."""


class JsonQuestionImporter(QuestionImporter):
    """Import a JSON array."""

    def import_file(self, path: str) -> tuple[list[dict], dict]:
        return _complete_import(load_question_file(path))


class CsvQuestionImporter(QuestionImporter):
    """Import CSV rows."""

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


def _complete_import(raw_records: list[dict]) -> tuple[list[dict], dict]:
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


def importer_for_path(path: str) -> QuestionImporter:
    """Select and directly construct a Concrete Product by suffix."""
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return JsonQuestionImporter()
    if suffix == ".csv":
        return CsvQuestionImporter()
    raise ValueError(f"unsupported question file extension: {suffix or '(none)'}")


def import_questions(path: str) -> tuple[list[dict], dict]:
    """Import through the directly constructed format-specific object."""
    return importer_for_path(path).import_file(path)
