import pytest

from quiz_platform.question_bank import (
    ApproveQuestionCommand,
    QuestionBankSession,
    RetireQuestionCommand,
)


def _questions() -> list[dict]:
    return [
        {"id": "Q-1", "status": "draft"},
        {"id": "Q-2", "status": "approved"},
    ]


def test_session_executes_commands_and_undoes_in_lifo_order():
    session = QuestionBankSession(_questions())
    assert session.can_undo is False

    session.execute(session.make_approve_command("Q-1"))
    session.execute(session.make_retire_command("Q-2"))
    assert session.can_undo is True
    assert session.status_of("Q-1") == "approved"
    assert session.status_of("Q-2") == "retired"

    assert session.undo_last() is True
    assert session.status_of("Q-2") == "approved"
    assert session.status_of("Q-1") == "approved"
    assert session.undo_last() is True
    assert session.status_of("Q-1") == "draft"
    assert session.undo_last() is False
    assert session.can_undo is False


def test_failed_command_is_not_added_to_history():
    session = QuestionBankSession(_questions())

    with pytest.raises(KeyError, match="unknown question ID"):
        session.execute(session.make_approve_command("Q-404"))

    assert session.can_undo is False
    assert session.undo_last() is False


def test_moderation_entry_points_create_the_corresponding_commands():
    session = QuestionBankSession(_questions())
    captured = []
    session.execute = lambda command: captured.append(command)

    session.approve_question("Q-1")
    session.retire_question("Q-2")

    assert [type(command) for command in captured] == [
        ApproveQuestionCommand,
        RetireQuestionCommand,
    ]


def test_session_returns_question_copies():
    session = QuestionBankSession(_questions())

    snapshot = session.questions
    snapshot[0]["status"] = "retired"

    assert session.status_of("Q-1") == "draft"


def test_execute_and_undo_record_audited_transitions():
    session = QuestionBankSession(_questions())

    session.approve_question("Q-1")
    assert session.undo_last() is True
    assert session.status_of("Q-1") == "draft"

    assert [entry["operation"] for entry in session.activity_log] == [
        "execute",
        "undo",
    ]
    assert all(entry["action"] == "approve" for entry in session.activity_log)
    assert session.activity_log[-1]["from_status"] == "approved"
    assert session.activity_log[-1]["to_status"] == "draft"
