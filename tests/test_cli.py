from pathlib import Path

from quiz_platform.question_bank.cli import _undo_message, main


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_cli_can_import_csv(capsys):
    exit_code = main(["import", str(DATA_DIR / "questions.csv")])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Import report" in output
    assert "accepted: 3" in output


def test_simple_interface_can_show_dashboard_then_quit(monkeypatch, capsys):
    answers = iter(["1", "5"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    exit_code = main(["interactive", str(DATA_DIR / "questions.json"), "--simple"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Question Bank TUI" in output
    assert "Question Bank Dashboard" in output
    assert "Goodbye." in output


def test_undo_feedback_checks_availability_before_invoking_undo():
    class EmptyHistorySession:
        can_undo = False

        def undo_last(self):
            raise AssertionError("undo_last must not be called for empty history")

    assert _undo_message(EmptyHistorySession()) == "Nothing to undo."

    class AvailableHistorySession:
        can_undo = True

        def __init__(self):
            self.undo_called = False

        def undo_last(self):
            self.undo_called = True
            return True

    session = AvailableHistorySession()
    assert _undo_message(session) == "Undone."
    assert session.undo_called is True
