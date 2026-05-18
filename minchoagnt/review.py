from __future__ import annotations

import re
from dataclasses import dataclass, field

from minchoagnt.sessions import Message


@dataclass(frozen=True)
class MemoryAddition:
    target: str
    content: str


@dataclass(frozen=True)
class SkillCreation:
    name: str
    content: str
    category: str = "learned"


@dataclass
class ReviewPlan:
    memory_additions: list[MemoryAddition] = field(default_factory=list)
    skill_creations: list[SkillCreation] = field(default_factory=list)


class ReviewEngine:
    """Heuristic reviewer that mimics Hermes' background reflection slot."""

    _remember = re.compile(r"\bremember(?:\s+that)?\s*[:\-]?\s*(.+)$", re.IGNORECASE)
    _skill = re.compile(
        r"\bskill\s*:\s*([a-zA-Z0-9 _-]+)\s*\|\s*(.+)$",
        re.IGNORECASE | re.DOTALL,
    )

    def review(
        self,
        messages: list[Message],
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
