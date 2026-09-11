"""Legacy session with conditional moderation history and undo."""

from typing import Iterable, Optional

from quiz_platform.question_bank.importers import import_questions


class QuestionBankSession:
    """Own imported questions and apply moderation actions directly."""

    def __init__(self, questions: Optional[Iterable[dict]] = None) -> None:
        self._questions = {}
        self._activity_log = []
        self._history = []
        if questions is not None:
            self._replace_questions(questions)

    @property
    def activity_log(self) -> list[dict]:
        return self._activity_log

    @property
    def questions(self) -> list[dict]:
        return [dict(question) for question in self._questions.values()]

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

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

    def status_of(self, question_id: str) -> str:
        return self._status_of(question_id)

    def import_file(self, path: str) -> tuple[list[dict], dict]:
        questions, report = import_questions(path)
        self._replace_questions(questions)
        self._history.clear()
        self._activity_log.append(
            {"action": "import", "path": path, "accepted": report["accepted"]}
        )
        return self.questions, report

    def approve_question(self, question_id: str) -> None:
        self._change_status(question_id, "approved", "approve")

    def retire_question(self, question_id: str) -> None:
        self._change_status(question_id, "retired", "retire")

    def _change_status(self, question_id: str, target: str, action: str) -> None:
        previous = self._status_of(question_id)
        self._set_status(question_id, target)
        self._history.append(
            {"question_id": question_id, "previous_status": previous, "action": action}
        )
        self._activity_log.append({"action": action, "question_id": question_id})

    def undo_last(self) -> bool:
        if not self._history:
            return False
        entry = self._history.pop()
        if entry["action"] in ("approve", "retire"):
            self._set_status(entry["question_id"], entry["previous_status"])
        self._activity_log.append({"action": "undo", "question_id": entry["question_id"]})
        return True
