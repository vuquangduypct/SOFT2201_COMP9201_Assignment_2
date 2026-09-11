"""Small command-line boundary for exercising the legacy snapshot."""

import argparse
import json
from typing import Optional

from quiz_platform.question_bank.core import build_candidate_pool
from quiz_platform.question_bank.session import QuestionBankSession


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quiz-bank-before")
    commands = parser.add_subparsers(dest="command", required=True)

    import_parser = commands.add_parser("import")
    import_parser.add_argument("questions_file")

    candidate_parser = commands.add_parser("candidates")
    candidate_parser.add_argument("questions_file")
    candidate_parser.add_argument("--request")

    moderate_parser = commands.add_parser("moderate")
    moderate_parser.add_argument("questions_file")
    moderate_parser.add_argument("action", choices=("approve", "retire"))
    moderate_parser.add_argument("question_id")
    return parser


def _load(path: str) -> tuple[QuestionBankSession, dict]:
    session = QuestionBankSession()
    _questions, report = session.import_file(path)
    return session, report


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    session, report = _load(args.questions_file)

    if args.command == "import":
        print(f"loaded: {report['loaded']}")
        print(f"accepted: {report['accepted']}")
        print(f"rejected: {report['rejected']}")
        return 0

    if args.command == "candidates":
        request = {}
        if args.request:
            with open(args.request, encoding="utf-8") as handle:
                request = json.load(handle)
            if not isinstance(request, dict):
                raise ValueError("request file must contain a JSON object")
        candidates, candidate_report = build_candidate_pool(session.questions, request)
        print(f"considered: {candidate_report['considered']}")
        print(f"eligible: {candidate_report['eligible']}")
        print("selected IDs: " + (", ".join(q["id"] for q in candidates) or "none"))
        return 0

    before = session.status_of(args.question_id)
    if args.action == "approve":
        session.approve_question(args.question_id)
    else:
        session.retire_question(args.question_id)
    print(f"{args.question_id}: {before} -> {session.status_of(args.question_id)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
