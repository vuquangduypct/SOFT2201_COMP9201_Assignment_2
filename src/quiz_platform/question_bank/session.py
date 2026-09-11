"""Question-bank session and command-based moderation history."""

from typing import Iterable, Optional

from quiz_platform.question_bank.commands import (
    ApproveQuestionCommand,
    ModerationCommand,
    RetireQuestionCommand,
)
from quiz_platform.question_bank.importers import import_questions


class QuestionBankSession:
    """Own questions and act as the Command Invoker and Receiver."""

    def __init__(self, questions: Optional[Iterable[dict]] = None) -> None:
        self._questions = {}
        self._activity_log = []
        self._command_history = []
        if questions is not None:
            self._replace_questions(questions)

    @property
    def activity_log(self) -> list[dict]:
        """Return the session activity entries."""
        return self._activity_log

    @property
    def questions(self) -> list[dict]:
        """Return copies of session-owned question records."""
        return [dict(question) for question in self._questions.values()]

    @property
    def can_undo(self) -> bool:
        # ??? TODO fill in
        raise NotImplementedError("??? TODO fill in")

    def _replace_questions(self, questions: Iterable[dict]) -> None:
        copied = {}
        for question in questions:
            question_id = question.get("id")
            if question_id in copied:
                raise ValueError(f"duplicate question ID: {question_id}")
            copied[question_id] = dict(question)
        self._questions = copied

    def _status_of(self, question_id: str) -> str:
        try:
            return self._questions[question_id]["status"]
        except KeyError as error:
            raise KeyError(f"unknown question ID: {question_id}") from error

    def _set_status(self, question_id: str, status: str) -> None:
        if question_id not in self._questions:
            raise KeyError(f"unknown question ID: {question_id}")
        self._questions[question_id]["status"] = status

    def _record_moderation(
        self,
        operation: str,
        action: str,
        question_id: str,
        from_status: str,
        to_status: str,
    ) -> None:
        self._activity_log.append(
            {
                "operation": operation,
                "action": action,
                "question_id": question_id,
                "from_status": from_status,
                "to_status": to_status,
            }
        )

    def status_of(self, question_id: str) -> str:
        return self._status_of(question_id)

    def import_file(self, path: str) -> tuple[list[dict], dict]:
        questions, report = import_questions(path)
        self._replace_questions(questions)
        self._command_history.clear()
        self._activity_log.append(
            {"operation": "import", "path": path, "accepted": report["accepted"]}
        )
        return self.questions, report

    def execute(self, command: ModerationCommand) -> None:
        """Execute a new command and retain it in history."""
        # ??? TODO fill in
        raise NotImplementedError("??? TODO fill in")

    def approve_question(self, question_id: str) -> None:
        self.execute(ApproveQuestionCommand(self, question_id))

    def retire_question(self, question_id: str) -> None:
        self.execute(RetireQuestionCommand(self, question_id))

    def undo_last(self) -> bool:
        """Undo and remove the latest command from history."""
        if not self._command_history:
            return False

        command = None  # ??? TODO remove the most recent command
        try:
            command.undo()
        except Exception:
            # ??? TODO we have to preserve history when undo fails
            raise
        return True

    def make_approve_command(self, question_id: str) -> ModerationCommand:
        return ApproveQuestionCommand(self, question_id)

    def make_retire_command(self, question_id: str) -> ModerationCommand:
        return RetireQuestionCommand(self, question_id)
