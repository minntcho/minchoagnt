from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from minchoagnt.sessions import Message

VALID_MEMORY_TARGETS = {"memory", "user"}
SAFE_SKILL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,79}$")
SAFE_CATEGORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


class ReviewPlanValidationError(ValueError):
    """Raised when reviewer output cannot be converted into a safe ReviewPlan."""


@dataclass(frozen=True)
class MemoryAddition:
    target: str
    content: str
    evidence: str | None = None

    def __post_init__(self) -> None:
        target = self.target.strip()
        if target not in VALID_MEMORY_TARGETS:
            raise ReviewPlanValidationError(
                f"memory target must be one of {sorted(VALID_MEMORY_TARGETS)}, got {self.target!r}."
            )
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "content", _required_text(self.content, "memory content"))
        object.__setattr__(self, "evidence", _optional_text(self.evidence, "memory evidence"))

    def to_dict(self) -> dict[str, str]:
        data = {"target": self.target, "content": self.content}
        if self.evidence is not None:
            data["evidence"] = self.evidence
        return data


@dataclass(frozen=True)
class SkillCreation:
    name: str
    content: str
    category: str | None = "learned"
    evidence: str | None = None

    def __post_init__(self) -> None:
        name = _required_text(self.name, "skill name")
        if not SAFE_SKILL_NAME.fullmatch(name):
            raise ReviewPlanValidationError(
                "skill name must start with a letter or number and contain only letters, "
                "numbers, spaces, underscores, or hyphens."
            )
        category = _optional_text(self.category, "skill category")
        if category is not None and not SAFE_CATEGORY.fullmatch(category):
            raise ReviewPlanValidationError(
                "skill category must start with a letter or number and contain only letters, "
                "numbers, underscores, or hyphens."
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "content", _required_text(self.content, "skill content"))
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "evidence", _optional_text(self.evidence, "skill evidence"))

    def to_dict(self) -> dict[str, str]:
        data = {"name": self.name, "content": self.content}
        if self.category is not None:
            data["category"] = self.category
        if self.evidence is not None:
            data["evidence"] = self.evidence
        return data


@dataclass
class ReviewPlan:
    memory_additions: list[MemoryAddition] = field(default_factory=list)
    skill_creations: list[SkillCreation] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.memory_additions = [
            item if isinstance(item, MemoryAddition) else _memory_from_dict(item)
            for item in self.memory_additions
        ]
        self.skill_creations = [
            item if isinstance(item, SkillCreation) else _skill_from_dict(item)
            for item in self.skill_creations
        ]

    @classmethod
    def from_json(cls, raw: str) -> "ReviewPlan":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReviewPlanValidationError(f"ReviewPlan JSON is invalid: {exc.msg}.") from exc
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewPlan":
        if not isinstance(data, dict):
            raise ReviewPlanValidationError("ReviewPlan JSON must be an object.")
        memory_additions = _list_field(data, "memory_additions")
        skill_creations = _list_field(data, "skill_creations")
        return cls(
            memory_additions=[_memory_from_dict(item) for item in memory_additions],
            skill_creations=[_skill_from_dict(item) for item in skill_creations],
        )

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "memory_additions": [item.to_dict() for item in self.memory_additions],
            "skill_creations": [item.to_dict() for item in self.skill_creations],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)


class ReviewEngine(Protocol):
    """Contract implemented by heuristic, fake, and future LLM reviewers."""

    def review(
        self,
        messages: Sequence[Message],
        review_memory: bool = True,
        review_skills: bool = True,
    ) -> ReviewPlan:
        """Return memory and skill candidates extracted from conversation messages."""


class RegexReviewEngine:
    """Heuristic reviewer that mimics Hermes' background reflection slot."""

    _remember = re.compile(r"\bremember(?:\s+that)?\s*[:\-]?\s*(.+)$", re.IGNORECASE)
    _skill = re.compile(
        r"\bskill\s*:\s*([a-zA-Z0-9 _-]+)\s*\|\s*(.+)$",
        re.IGNORECASE | re.DOTALL,
    )

    def review(
        self,
        messages: Sequence[Message],
        review_memory: bool = True,
        review_skills: bool = True,
    ) -> ReviewPlan:
        plan = ReviewPlan()
        for message in messages:
            if message.role != "user":
                continue
            if review_memory:
                addition = self._memory_from_text(message.content)
                if addition:
                    plan.memory_additions.append(addition)
            if review_skills:
                skill = self._skill_from_text(message.content)
                if skill:
                    plan.skill_creations.append(skill)
        return plan

    def _memory_from_text(self, text: str) -> MemoryAddition | None:
        match = self._remember.search(text.strip())
        if not match:
            return None
        fact = match.group(1).strip()
        if not fact:
            return None
        target = "user" if self._looks_user_profile_fact(fact) else "memory"
        return MemoryAddition(target=target, content=fact)

    def _skill_from_text(self, text: str) -> SkillCreation | None:
        match = self._skill.search(text.strip())
        if not match:
            return None
        name = match.group(1).strip()
        raw_steps = match.group(2).strip()
        steps = [step.strip() for step in raw_steps.split(";") if step.strip()]
        if not name or not steps:
            return None
        content = self._skill_content(name, steps)
        return SkillCreation(name=name, content=content)

    @staticmethod
    def _looks_user_profile_fact(fact: str) -> bool:
        lowered = fact.lower()
        return any(
            marker in lowered
            for marker in [
                "i prefer",
                "my ",
                "i use",
                "i work",
                "i am",
                "i'm",
                "me ",
            ]
        )

    @staticmethod
    def _skill_content(name: str, steps: list[str]) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower()).strip("-")
        title = slug.replace("-", " ").title()
        numbered = "\n".join(f"{idx}. {step}" for idx, step in enumerate(steps, start=1))
        return f"""---
name: {slug}
description: Agent-created workflow captured from conversation.
---

# {title}

## When To Use

Use this when the same workflow appears again.

## Procedure

{numbered}

## Verification

Confirm the final step completed and summarize any files, commands, or decisions involved.
"""


def _memory_from_dict(data: Any) -> MemoryAddition:
    if not isinstance(data, dict):
        raise ReviewPlanValidationError("memory_additions entries must be objects.")
    return MemoryAddition(
        target=_required_key(data, "target", "memory addition"),
        content=_required_key(data, "content", "memory addition"),
        evidence=data.get("evidence"),
    )


def _skill_from_dict(data: Any) -> SkillCreation:
    if not isinstance(data, dict):
        raise ReviewPlanValidationError("skill_creations entries must be objects.")
    return SkillCreation(
        name=_required_key(data, "name", "skill creation"),
        content=_required_key(data, "content", "skill creation"),
        category=data.get("category", "learned"),
        evidence=data.get("evidence"),
    )


def _list_field(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise ReviewPlanValidationError(f"{key} must be a list.")
    return value


def _required_key(data: dict[str, Any], key: str, context: str) -> str:
    if key not in data:
        raise ReviewPlanValidationError(f"{context} is missing required field {key!r}.")
    return _required_text(data[key], key)


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ReviewPlanValidationError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ReviewPlanValidationError(f"{field_name} cannot be empty.")
    return cleaned


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ReviewPlanValidationError(f"{field_name} must be a string when present.")
    cleaned = value.strip()
    return cleaned or None
