"""Moderation Command participants with undo and audit behavior."""

from abc import ABC, abstractmethod
from typing import Optional


class ModerationCommand(ABC):
    """Command interface for a reversible moderation action."""

    @property
    @abstractmethod
    def question_id(self) -> str:
        """Return the affected question ID."""

    @abstractmethod
    def execute(self) -> None:
        """Apply the moderation action for the first time."""

    @abstractmethod
    def undo(self) -> None:
        """Restore the exact state that preceded execution."""

class _ChangeStatusCommand(ModerationCommand):
    """Shared state transition, audit, and undo mechanics."""

    action_name = ""
    target_status = ""

    def __init__(self, receiver, question_id: str) -> None:
        self._receiver = receiver
        self._question_id = question_id
        self._previous_status: Optional[str] = None
        self._state = "new"

    @property
    def question_id(self) -> str:
        return self._question_id

    def execute(self) -> None:
        # ??? TODO fill in
        raise NotImplementedError("??? TODO fill in")

    def undo(self) -> None:
        """Restore the state that preceded this command's execution."""
        if self._state != "executed" or self._previous_status is None:
            raise RuntimeError("only an executed command can be undone")

        current_status = self._receiver._status_of(self._question_id)
        if current_status != self.target_status:
            raise RuntimeError("question status changed outside command history")

        restored_status = None  # ??? TODO select the status to restore

        self._receiver._set_status(self._question_id, restored_status)
        self._receiver._record_moderation(
            "undo",
            self.action_name,
            self._question_id,
            current_status,
            restored_status,
        )
        self._state = ""  # ??? TODO record the command's new lifecycle state

class ApproveQuestionCommand(_ChangeStatusCommand):
    """Approve a question and retain enough state to undo it."""

    action_name = "approve"
    target_status = "approved"


class RetireQuestionCommand(_ChangeStatusCommand):
    """Retire a question and retain enough state to undo it."""

    action_name = "retire"
    target_status = "retired"
