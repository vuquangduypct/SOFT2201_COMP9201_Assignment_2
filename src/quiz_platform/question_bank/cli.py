"""Command-line and terminal interfaces for the quiz platform."""

import argparse
import json
import sys
import textwrap
from typing import Optional

try:
    import curses
except ImportError:
    curses = None

from quiz_platform.question_bank.core import build_candidate_pool
from quiz_platform.question_bank.session import QuestionBankSession


def _load_request(path: Optional[str]) -> dict:
    if path is None:
        return {}
    with open(path, encoding="utf-8") as handle:
        request = json.load(handle)
    if not isinstance(request, dict):
        raise ValueError("request file must contain a JSON object")
    return request


def _print_import_report(report: dict) -> None:
    print("Import report")
    print(f"  loaded: {report['loaded']}")
    print(f"  accepted: {report['accepted']}")
    print(f"  rejected: {report['rejected']}")
    print(f"  duplicate warnings: {len(report['duplicate_warnings'])}")


def _print_candidate_report(candidates: list[dict], report: dict) -> None:
    print("Candidate pool")
    print(f"  considered: {report['considered']}")
    print(f"  eligible: {report['eligible']}")
    print(f"  rule: {report['rule_expression']}")
    for reason in ("id", "status", "topic", "format", "difficulty", "reuse"):
        identifiers = report[f"excluded_by_{reason}"]
        print(f"  excluded by {reason}: {len(identifiers)}")
    print("  selected IDs: " + (", ".join(q["id"] for q in candidates) or "none"))


def _load_session(path: str) -> tuple[QuestionBankSession, dict]:
    session = QuestionBankSession()
    _questions, report = session.import_file(path)
    return session, report


def _candidate_result(state: dict) -> tuple[list[dict], dict]:
    return build_candidate_pool(
        state["session"].questions,
        state["request"],
        reference_date=state["reference_date"],
    )


def _print_dashboard(state: dict) -> None:
    questions = state["session"].questions
    statuses = {}
    topics = {}
    for question in questions:
        status = question.get("status", "unknown")
        topic = question.get("topic", "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        topics[topic] = topics.get(topic, 0) + 1
    print("Question Bank Dashboard")
    print(f"  questions: {len(questions)}")
    print("  status: " + ", ".join(f"{key}={value}" for key, value in sorted(statuses.items())))
    print("  topics: " + ", ".join(f"{key}={value}" for key, value in sorted(topics.items())))


def _print_questions(session: QuestionBankSession) -> None:
    print("ID       Status     Topic                 Text")
    print("-" * 72)
    for question in session.questions:
        text = question.get("text", "")
        if len(text) > 34:
            text = text[:33] + "..."
        print(
            f"{question.get('id', ''):<8} "
            f"{question.get('status', ''):<10} "
            f"{question.get('topic', ''):<21} {text}"
        )


def _undo_message(session: QuestionBankSession) -> str:
    """Undo when history is available and return user-facing feedback."""
    if not session.can_undo:
        return "Nothing to undo."
    return "Undone." if session.undo_last() else "Nothing to undo."


def _run_simple_moderation(state: dict) -> None:
    session = state["session"]
    while True:
        print()
        print("Moderation")
        _print_questions(session)
        action = input("Action [a approve, r retire, u undo, q menu]: ").strip().lower()
        if action in ("q", "quit", "menu"):
            return
        if action in ("u", "undo"):
            print(_undo_message(session))
            continue
        if action not in ("a", "approve", "r", "retire"):
            print("Unknown action.")
            continue
        question_id = input("Question ID: ").strip()
        try:
            if action in ("a", "approve"):
                session.approve_question(question_id)
            else:
                session.retire_question(question_id)
        except KeyError as error:
            print(error)
        else:
            print(f"{question_id}: {session.status_of(question_id)}")


def _run_simple_rehearsal(state: dict) -> None:
    candidates, _report = _candidate_result(state)
    print("Quiz rehearsal")
    if not candidates:
        print("  no eligible questions")
        return
    for index, question in enumerate(candidates, start=1):
        print(f"  {index}. {question['id']}: {question['text']}")
        answer = input("     Enter to reveal, s to skip, q to stop: ").strip().lower()
        if answer == "q":
            return
        if answer != "s":
            wrapped = textwrap.wrap(question.get("model_answer", "Not provided."), width=62)
            for line in wrapped:
                print(f"     {line}")


def _run_simple(state: dict) -> None:
    while True:
        print()
        print("Question Bank TUI")
        print("  1. Dashboard")
        print("  2. Candidate pool")
        print("  3. Moderation")
        print("  4. Quiz rehearsal")
        print("  5. Quit")
        choice = input("Choose: ").strip()
        print()
        if choice == "1":
            _print_dashboard(state)
        elif choice == "2":
            candidates, report = _candidate_result(state)
            _print_candidate_report(candidates, report)
        elif choice == "3":
            _run_simple_moderation(state)
        elif choice == "4":
            _run_simple_rehearsal(state)
        elif choice in ("5", "q", "quit"):
            print("Goodbye.")
            return
        else:
            print("Unknown choice.")


def _safe_add(screen, row: int, column: int, text: str, style: int = 0) -> None:
    height, width = screen.getmaxyx()
    if row < 0 or row >= height or column >= width:
        return
    try:
        screen.addnstr(row, column, text, max(0, width - column - 1), style)
    except curses.error:
        pass


def _draw_full_screen(screen, state: dict, tab: int, selected: int, message: str) -> None:
    screen.erase()
    tabs = ("Dashboard", "Candidates", "Moderation")
    _safe_add(screen, 0, 0, " Quiz Generator Maintenance Console ", curses.A_REVERSE)
    column = 0
    for index, label in enumerate(tabs):
        text = f" {index + 1}:{label} "
        _safe_add(screen, 2, column, text, curses.A_REVERSE if index == tab else 0)
        column += len(text) + 1

    questions = state["session"].questions
    row = 4
    if tab == 0:
        statuses = {}
        for question in questions:
            status = question.get("status", "unknown")
            statuses[status] = statuses.get(status, 0) + 1
        _safe_add(screen, row, 0, f"Imported questions: {len(questions)}", curses.A_BOLD)
        for status, count in sorted(statuses.items()):
            row += 2
            _safe_add(screen, row, 2, f"{status:<10} {'#' * count} {count}")
    elif tab == 1:
        candidates, report = _candidate_result(state)
        _safe_add(
            screen,
            row,
            0,
            f"Considered {report['considered']} | eligible {report['eligible']} | "
            f"reuse exclusions {len(report['excluded_by_reuse'])}",
            curses.A_BOLD,
        )
        row += 1
        _safe_add(screen, row, 0, f"Rule: {report['rule_expression']}")
        for question in candidates:
            row += 2
            _safe_add(screen, row, 2, f"{question['id']}  {question['topic']}  {question['text']}")
    else:
        _safe_add(
            screen,
            row,
            0,
            "Use up/down, a approve, x retire, u undo",
            curses.A_BOLD,
        )
        for index, question in enumerate(questions):
            row += 1
            marker = ">" if index == selected else " "
            style = curses.A_REVERSE if index == selected else 0
            _safe_add(
                screen,
                row,
                0,
                f"{marker} {question['id']:<8} {question['status']:<10} {question['text']}",
                style,
            )

    height, _width = screen.getmaxyx()
    _safe_add(screen, height - 2, 0, message)
    _safe_add(
        screen,
        height - 1,
        0,
        " q quit | left/right view | 1-3 jump | moderation: a/x/u ",
        curses.A_REVERSE,
    )
    screen.refresh()


def _full_screen_loop(screen, state: dict) -> None:
    curses.curs_set(0)
    screen.keypad(True)
    tab = 0
    selected = 0
    message = ""
    while True:
        questions = state["session"].questions
        selected = min(selected, max(0, len(questions) - 1))
        _draw_full_screen(screen, state, tab, selected, message)
        key = screen.getch()
        message = ""
        if key in (ord("q"), 27):
            return
        if key in (curses.KEY_RIGHT, ord("l")):
            tab = min(tab + 1, 2)
        elif key in (curses.KEY_LEFT, ord("h")):
            tab = max(tab - 1, 0)
        elif key in (ord("1"), ord("2"), ord("3")):
            tab = key - ord("1")
        elif tab == 2 and key == curses.KEY_DOWN:
            selected = min(selected + 1, max(0, len(questions) - 1))
        elif tab == 2 and key == curses.KEY_UP:
            selected = max(selected - 1, 0)
        elif tab == 2 and key == ord("u"):
            message = _undo_message(state["session"])
        elif tab == 2 and questions and key in (ord("a"), ord("x")):
            question_id = questions[selected]["id"]
            if key == ord("a"):
                state["session"].approve_question(question_id)
            else:
                state["session"].retire_question(question_id)
            message = f"{question_id}: {state['session'].status_of(question_id)}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quiz-bank")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser(
        "import",
        help="import JSON, JSON Lines, or CSV questions",
    )
    import_parser.add_argument("questions_file")

    candidate_parser = subparsers.add_parser("candidates", help="construct a candidate pool")
    candidate_parser.add_argument("questions_file")
    candidate_parser.add_argument("--request")
    candidate_parser.add_argument("--reference-date")

    moderate_parser = subparsers.add_parser("moderate", help="apply one in-memory moderation action")
    moderate_parser.add_argument("questions_file")
    moderate_parser.add_argument("action", choices=("approve", "retire"))
    moderate_parser.add_argument("question_id")

    interactive_parser = subparsers.add_parser("interactive", help="open the terminal interface")
    interactive_parser.add_argument("questions_file", nargs="?", default="data/questions.json")
    interactive_parser.add_argument("--request")
    interactive_parser.add_argument("--reference-date")
    interactive_parser.add_argument("--simple", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "import":
        _session, report = _load_session(args.questions_file)
        _print_import_report(report)
        return 0

    if args.command == "candidates":
        session, import_report = _load_session(args.questions_file)
        request = _load_request(args.request)
        candidates, candidate_report = build_candidate_pool(
            session.questions,
            request,
            reference_date=args.reference_date,
        )
        _print_import_report(import_report)
        _print_candidate_report(candidates, candidate_report)
        return 0

    if args.command == "moderate":
        session, _report = _load_session(args.questions_file)
        before = session.status_of(args.question_id)
        if args.action == "approve":
            session.approve_question(args.question_id)
        else:
            session.retire_question(args.question_id)
        print(f"{args.question_id}: {before} -> {session.status_of(args.question_id)}")
        return 0

    session, import_report = _load_session(args.questions_file)
    state = {
        "session": session,
        "import_report": import_report,
        "request": _load_request(args.request),
        "reference_date": args.reference_date,
    }
    if args.simple or curses is None or not sys.stdin.isatty() or not sys.stdout.isatty():
        _run_simple(state)
    else:
        curses.wrapper(_full_screen_loop, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
