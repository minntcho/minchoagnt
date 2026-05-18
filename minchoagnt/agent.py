from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minchoagnt.memory import MemoryStore
from minchoagnt.review import ReviewEngine, ReviewPlan
from minchoagnt.sessions import SessionDB
from minchoagnt.skills import SkillExistsError, SkillStore


@dataclass(frozen=True)
class ReviewSummary:
    memory_saved: int = 0
    skills_created: int = 0


@dataclass(frozen=True)
class ChatResult:
    session_id: str
    response: str
    review: ReviewSummary


class MiniAgent:
    """Small orchestration shell around memory, skills, sessions, and review."""

    def __init__(
        self,
        home: Path | str,
        memory_interval: int = 10,
        skill_interval: int = 10,
        session_id: str | None = None,
    ):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.memory = MemoryStore(self.home).load()
        self.skills = SkillStore(self.home)
        self.sessions = SessionDB(self.home / "state.db")
        self.review_engine = ReviewEngine()
        self.session_id = session_id or self.sessions.create_session(source="cli")
        self.memory_interval = max(1, memory_interval)
        self.skill_interval = max(1, skill_interval)
        self._turns_since_memory = 0
        self._iters_since_skill = 0

    def context(self) -> str:
        memory = MemoryStore(self.home).load()
        sections = ["# MiniAgent Context"]
        for target in ("user", "memory"):
            snapshot = memory.snapshot(target)  # type: ignore[arg-type]
            if snapshot:
                sections.append(snapshot)
        skill_names = self.skills.list_names()
        if skill_names:
            sections.append("Available skills:\n" + "\n".join(f"- {name}" for name in skill_names))
        else:
            sections.append("Available skills: none")
        return "\n\n".join(sections)

    def chat(self, user_text: str, tool_iterations: int = 0) -> ChatResult:
        self.sessions.append_message(self.session_id, "user", user_text)
        response = self._response_for(user_text)
        self.sessions.append_message(self.session_id, "assistant", response)

        self._turns_since_memory += 1
        self._iters_since_skill += max(0, tool_iterations)

        memory_saved = 0
        skills_created = 0
        messages = self.sessions.get_messages(self.session_id)

        if self._turns_since_memory >= self.memory_interval:
            plan = self.review_engine.review(messages, review_memory=True, review_skills=False)
            memory_saved = self._apply_memory(plan)
            self._turns_since_memory = 0

        if self._iters_since_skill >= self.skill_interval:
            plan = self.review_engine.review(messages, review_memory=False, review_skills=True)
            skills_created = self._apply_skills(plan)
            self._iters_since_skill = 0

        return ChatResult(
            session_id=self.session_id,
            response=response,
            review=ReviewSummary(memory_saved=memory_saved, skills_created=skills_created),
        )

    def _apply_memory(self, plan: ReviewPlan) -> int:
        count = 0
        for addition in plan.memory_additions:
            if self.memory.add(addition.target, addition.content):  # type: ignore[arg-type]
                count += 1
        return count

    def _apply_skills(self, plan: ReviewPlan) -> int:
        count = 0
        for creation in plan.skill_creations:
            try:
                self.skills.create(creation.name, creation.content, category=creation.category)
            except SkillExistsError:
                continue
            count += 1
        return count

    @staticmethod
    def _response_for(user_text: str) -> str:
        lowered = user_text.lower()
        if "remember" in lowered:
            return "Queued that fact for the next memory review."
        if "skill:" in lowered:
            return "Queued that workflow for the next skill review."
        return "Recorded this turn."
