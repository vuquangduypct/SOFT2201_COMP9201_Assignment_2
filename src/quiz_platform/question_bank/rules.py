"""Eligibility-rule participants for the Composite refactoring."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, Optional


class EligibilityRule(ABC):
    """Component that evaluates and renders one eligibility expression."""

    @abstractmethod
    def exclusion_reason(self, question: dict) -> Optional[str]:
        """Return a report suffix such as 'topic', or None when eligible."""

    @abstractmethod
    def render(self) -> str:
        """Return this rule as an equation-like expression."""


def _render_set(values: Iterable[object]) -> str:
    return "{" + ", ".join(sorted(str(value) for value in values)) + "}"


class ExcludedIdRule(EligibilityRule):
    """Exclude question IDs explicitly named by a request."""

    def __init__(self, excluded_ids: Iterable[str]) -> None:
        self._excluded_ids = frozenset(excluded_ids)

    def exclusion_reason(self, question: dict) -> Optional[str]:
        if question.get("id") in self._excluded_ids:
            return "id"
        return None

    def render(self) -> str:
        return f"id NOT IN {_render_set(self._excluded_ids)}"


class RequiredStatusRule(EligibilityRule):
    """Require one status when a request specifies it."""

    def __init__(self, required_status: Optional[str]) -> None:
        self._required_status = required_status

    def exclusion_reason(self, question: dict) -> Optional[str]:
        if self._required_status is not None and question.get("status") != self._required_status:
            return "status"
        return None

    def render(self) -> str:
        return f"status = {self._required_status}"


class _AllowedValuesRule(EligibilityRule):
    """Shared implementation for a field constrained to allowed values."""

    def __init__(self, field: str, values: Iterable[object], reason: str) -> None:
        allowed = frozenset(values)
        self._allowed = allowed or None
        self._field = field
        self._reason = reason

    def exclusion_reason(self, question: dict) -> Optional[str]:
        if self._allowed is not None and question.get(self._field) not in self._allowed:
            return self._reason
        return None

    def render(self) -> str:
        return f"{self._field} IN {_render_set(self._allowed or [])}"


class TopicRule(_AllowedValuesRule):
    def __init__(self, topics: Iterable[str]) -> None:
        super().__init__("topic", topics, "topic")


class FormatRule(_AllowedValuesRule):
    def __init__(self, formats: Iterable[str]) -> None:
        super().__init__("format", formats, "format")


class DifficultyRule(_AllowedValuesRule):
    def __init__(self, difficulties: Iterable[int]) -> None:
        super().__init__("difficulty", difficulties, "difficulty")


class AllOfRule(EligibilityRule):
    """Composite requiring every child rule to accept the question."""

    def __init__(self, children: Iterable[EligibilityRule]) -> None:
        self._children = tuple(children)

    @property
    def children(self) -> tuple[EligibilityRule, ...]:
        return self._children

    def exclusion_reason(self, question: dict) -> Optional[str]:
        """Return the first child exclusion in declared order."""
        # ??? TODO fill in
        for child in self._children:
            reason = child.exclusion_reason(question)
            if reason is not None:
                return reason
            else:
                # raise NotImplementedError("??? TODO fill in") 
                raise NotImplementedError("The exclusion reason has not been implemented yet!")
        return None

    def render(self) -> str:
        """Render nested children using the same Component interface."""
        # ??? TODO fill in
        if not self._children:
            return "TRUE"
        else: 
            raise NotImplementedError("The render method has not been implemented yet!")
        return " AND ".join(f"{child.render()}" for child in self._children)
        # raise NotImplementedError("??? TODO fill in")


class ReuseCooldownRule(EligibilityRule):
    """Exclude recently used questions relative to a fixed date."""

    def __init__(self, reference_date: str, cooldown_days: int) -> None:
        if isinstance(cooldown_days, bool) or not isinstance(cooldown_days, int) or cooldown_days < 0:
            raise ValueError("reuse_cooldown_days must be a non-negative integer")
        try:
            self._reference_date = date.fromisoformat(reference_date)
        except (TypeError, ValueError) as error:
            raise ValueError("reference_date must be YYYY-MM-DD") from error
        self._cooldown_days = cooldown_days

    def exclusion_reason(self, question: dict) -> Optional[str]:
        """Return 'reuse' only when the question is inside the cooldown."""
        # ??? TODO fill in
        for q in self.question:
            question_date = q.render()
            day_difference = self._reference_date - question_date
            if question_date is not None and day_difference < self._cooldown_days:
                return "reuse"
            else:
                # raise NotImplementedError("??? TODO fill in")
                raise NotImplementedError("The exclusion reason has not been implemented yet!")

        return None

    def render(self) -> str:
        return (
            "(last_used IS NULL OR "
            f"days_since(last_used, {self._reference_date.isoformat()}) >= "
            f"{self._cooldown_days})"
        )


def rules_from_request(request: dict, reference_date: Optional[str]) -> EligibilityRule:
    """ the ordered rule tree described by one quiz request."""
    children = []
    if request.get("exclude_ids"):
        children.append(ExcludedIdRule(request["exclude_ids"]))
    if request.get("required_status") is not None:
        children.append(RequiredStatusRule(request["required_status"]))
    if request.get("topics"):
        children.append(TopicRule(request["topics"]))
    if request.get("formats"):
        children.append(FormatRule(request["formats"]))
    if request.get("difficulty"):
        children.append(DifficultyRule(request["difficulty"]))

    cooldown_days = request.get("reuse_cooldown_days")
    if cooldown_days is not None:
        if isinstance(cooldown_days, bool) or not isinstance(cooldown_days, int) or cooldown_days < 0:
            raise ValueError("reuse_cooldown_days must be a non-negative integer")
        if cooldown_days > 0:
            if reference_date is None:
                raise ValueError("reference_date is required for a positive reuse cooldown")
            children.append(ReuseCooldownRule(reference_date, cooldown_days))

    return AllOfRule(children)
