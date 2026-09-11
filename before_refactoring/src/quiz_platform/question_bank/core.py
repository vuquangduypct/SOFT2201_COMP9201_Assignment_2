"""Question validation and legacy candidate-pool construction."""

import json
import re
from datetime import date
from typing import Optional

SUPPORTED_FORMATS = {"multiple_choice", "short_answer", "true_false", "code_reading"}
SUPPORTED_STATUSES = {"draft", "approved", "retired"}


def empty_import_report(errors=[]):
    """Create the counters and diagnostics collected during an import."""
    return {
        "loaded": 0,
        "accepted": 0,
        "rejected": 0,
        "duplicate_warnings": [],
        "errors": errors,
    }


def empty_eligibility_report() -> dict:
    """Return a fresh candidate-pool report."""
    return {
        "considered": 0,
        "eligible": 0,
        "excluded_by_status": [],
        "excluded_by_topic": [],
        "excluded_by_format": [],
        "excluded_by_difficulty": [],
        "excluded_by_id": [],
        "excluded_by_reuse": [],
    }


def load_question_file(path: str) -> list[dict]:
    """Read question records from a JSON file."""
    try:
        with open(path, encoding="utf-8") as handle:
            records = json.load(handle)
        if not isinstance(records, list):
            raise ValueError("question file must contain a JSON array")
        return records
    except ValueError:
        raise
    except Exception:
        return []


def _identifier(value):
    if not isinstance(value, str):
        return value
    return re.sub(r"[\s-]+", "_", value.strip().lower())


def _string_list(value):
    if not isinstance(value, list):
        return value
    result = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            result.append(item)
            continue
        normalised = _identifier(item)
        if normalised and normalised not in seen:
            result.append(normalised)
            seen.add(normalised)
    return result


def normalise_question(record: dict) -> dict:
    """Return a normalised copy of one question record."""
    question = dict(record)
    if isinstance(question.get("id"), str):
        question["id"] = question["id"].strip()
    if isinstance(question.get("text"), str):
        question["text"] = re.sub(r"\s+", " ", question["text"].strip())
    if isinstance(question.get("format"), str):
        question["format"] = question["format"].strip().lower()
    if "topic" in question:
        question["topic"] = _identifier(question["topic"])
    if isinstance(question.get("difficulty"), str) and question["difficulty"].strip().isdigit():
        question["difficulty"] = int(question["difficulty"])
    if isinstance(question.get("status"), str):
        question["status"] = question["status"].strip().lower()
    if isinstance(question.get("estimated_minutes"), str) and question[
        "estimated_minutes"
    ].strip().isdigit():
        question["estimated_minutes"] = int(question["estimated_minutes"])
    if "tags" in question:
        question["tags"] = _string_list(question["tags"])
    if "learning_outcomes" in question:
        question["learning_outcomes"] = _string_list(question["learning_outcomes"])
    if isinstance(question.get("last_used"), str):
        question["last_used"] = question["last_used"].strip() or None
    return question


def validate_question(question: dict) -> list[str]:
    """Return validation messages; an empty list means valid."""
    if not isinstance(question, dict):
        return ["record must be a dictionary"]

    errors = []
    question_id = question.get("id")
    if not isinstance(question_id, str) or not re.fullmatch(r"Q-\d+", question_id):
        errors.append("id must match Q-<digits>")
    if not isinstance(question.get("text"), str) or question["text"].strip() == "":
        errors.append(f"{question_id}: text is required")
    if question.get("format") not in SUPPORTED_FORMATS:
        errors.append(f"{question_id}: unsupported format")
    if not isinstance(question.get("topic"), str) or question["topic"].strip() == "":
        errors.append(f"{question_id}: topic is required")
    if question.get("difficulty") not in (1, 2, 3):
        errors.append(f"{question_id}: difficulty must be 1, 2, or 3")
    outcomes = question.get("learning_outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        errors.append(f"{question_id}: learning_outcomes must be a non-empty list")
    if question.get("status") not in SUPPORTED_STATUSES:
        errors.append(f"{question_id}: unsupported status")
    if not isinstance(question.get("estimated_minutes"), int) or question[
        "estimated_minutes"
    ] <= 0:
        errors.append(f"{question_id}: estimated_minutes must be greater than zero")
    if not isinstance(question.get("tags"), list):
        errors.append(f"{question_id}: tags must be a list")
    if question.get("last_used") is not None:
        try:
            date.fromisoformat(question["last_used"])
        except (TypeError, ValueError):
            errors.append(f"{question_id}: last_used must be YYYY-MM-DD or null")
    return errors


def split_valid_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return accepted records and rejection entries."""
    accepted = []
    rejected = []
    for question in records:
        errors = validate_question(question)
        if errors:
            rejected.append({"id": question.get("id"), "errors": errors})
        else:
            accepted.append(question)
    return accepted, rejected


def _duplicate_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold())


def find_duplicates(records: list[dict]) -> list[dict]:
    """Return duplicate-warning records."""
    warnings = []
    seen = {}
    for question in records:
        key = _duplicate_key(question.get("text", ""))
        if key in seen:
            warnings.append(
                {
                    "question_id": question.get("id"),
                    "matches_id": seen[key],
                    "kind": "normalised_text",
                }
            )
        else:
            seen[key] = question.get("id")
    return warnings


def build_candidate_pool(
    questions: list[dict],
    request: dict,
    *,
    reference_date: Optional[str] = None,
) -> tuple[list[dict], dict]:
    """Return eligible questions and an eligibility report without changing the input records."""
    report = empty_eligibility_report()
    eligible = []
    topics = set(request.get("topics", [])) or None
    formats = set(request.get("formats", [])) or None
    difficulties = set(request.get("difficulty", [])) or None
    excluded_ids = set(request.get("exclude_ids", []))
    required_status = request.get("required_status")

    for question in questions:
        report["considered"] += 1
        question_id = question.get("id")
        question["checked_on"] = reference_date or str(date.today())
        if question_id in excluded_ids:
            report["excluded_by_id"].append(question_id)
            continue
        if required_status is not None and question.get("status") != required_status:
            report["excluded_by_status"].append(question_id)
            continue
        if topics is not None and question.get("topic") not in topics:
            report["excluded_by_topic"].append(question_id)
            continue
        if formats is not None and question.get("format") not in formats:
            report["excluded_by_format"].append(question_id)
            continue
        if difficulties is not None and question.get("difficulty") not in difficulties:
            report["excluded_by_difficulty"].append(question_id)
            continue
        eligible.append(question)

    report["eligible"] = len(eligible)
    return eligible, report
