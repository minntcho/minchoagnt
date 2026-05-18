from __future__ import annotations

import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, Sequence

from minchoagnt.memory import MemoryErrorBase, MemoryStore
from minchoagnt.ollama import OllamaReviewEngine
from minchoagnt.review import RegexReviewEngine, ReviewEngine, ReviewPlan
from minchoagnt.sessions import Message
from minchoagnt.skills import SkillError, SkillExistsError, SkillStore

NodeStatus = Literal["pending", "running", "success", "error", "no-op"]


@dataclass(frozen=True)
class WorkbenchInput:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class WorkbenchReviewer:
    type: str
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, **self.config}


@dataclass(frozen=True)
class WorkbenchEvent:
    step: str
    status: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"step": self.step, "status": self.status, "message": self.message}


@dataclass(frozen=True)
class ApplyResult:
    memory_saved: int = 0
    memory_duplicates: int = 0
    memory_failed: int = 0
    skills_created: int = 0
    skill_duplicates: int = 0
    skill_failed: int = 0
    empty_plan: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, int | bool | list[str]]:
        return {
            "memory_saved": self.memory_saved,
            "memory_duplicates": self.memory_duplicates,
            "memory_failed": self.memory_failed,
            "skills_created": self.skills_created,
            "skill_duplicates": self.skill_duplicates,
            "skill_failed": self.skill_failed,
            "empty_plan": self.empty_plan,
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class CheckResult:
    target: str = ""
    contains: str = ""
    passed: bool = False
    message: str = "not run"

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "target": self.target,
            "contains": self.contains,
            "passed": self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class ListDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "added": list(self.added),
            "removed": list(self.removed),
            "unchanged": list(self.unchanged),
        }


@dataclass(frozen=True)
class SkillDiff:
    created: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[str]]:
        return {"created": list(self.created), "unchanged": list(self.unchanged)}


@dataclass(frozen=True)
class WorkbenchDiff:
    memory: ListDiff = field(default_factory=ListDiff)
    user: ListDiff = field(default_factory=ListDiff)
    skills: SkillDiff = field(default_factory=SkillDiff)

    def to_dict(self) -> dict[str, dict[str, list[str]]]:
        return {
            "memory": self.memory.to_dict(),
            "user": self.user.to_dict(),
            "skills": self.skills.to_dict(),
        }


@dataclass(frozen=True)
class WorkbenchRun:
    run_id: str
    input: WorkbenchInput
    reviewer: WorkbenchReviewer
    review_plan: ReviewPlan
    apply_result: ApplyResult = field(default_factory=ApplyResult)
    diff: WorkbenchDiff = field(default_factory=WorkbenchDiff)
    check_result: CheckResult = field(default_factory=CheckResult)
    events: list[WorkbenchEvent] = field(default_factory=list)
    node_status: dict[str, NodeStatus] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "input": self.input.to_dict(),
            "reviewer": self.reviewer.to_dict(),
            "review_plan": self.review_plan.to_dict(),
            "apply_result": self.apply_result.to_dict(),
            "diff": self.diff.to_dict(),
            "check_result": self.check_result.to_dict(),
            "events": [event.to_dict() for event in self.events],
            "node_status": dict(self.node_status),
        }


class FakeReviewEngine:
    """Deterministic reviewer for tests and future UI demos."""

    def __init__(self, plan: ReviewPlan | None = None):
        self.plan = plan if plan is not None else ReviewPlan()

    def review(
        self,
        messages: Sequence[Message],
        review_memory: bool = True,
        review_skills: bool = True,
    ) -> ReviewPlan:
        plan = ReviewPlan.from_dict(self.plan.to_dict())
        if not review_memory:
            plan.memory_additions = []
        if not review_skills:
            plan.skill_creations = []
        return plan


class ReviewWorkbench:
    """Runs the review/apply cycle behind the Review Workbench UI."""

    def __init__(
        self,
        home: Path | str,
        reviewer_type: str = "regex",
        review_engine: ReviewEngine | None = None,
        reviewer_config: dict[str, Any] | None = None,
    ):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.reviewer_type = reviewer_type
        self.reviewer_config = dict(reviewer_config or {})
        self.review_engine = review_engine or self._reviewer_for(
            reviewer_type, self.reviewer_config
        )
        self._run_count = 0
        self._sandbox: tempfile.TemporaryDirectory[str] | None = None

    @classmethod
    def sandbox(
        cls,
        reviewer_type: str = "regex",
        review_engine: ReviewEngine | None = None,
        reviewer_config: dict[str, Any] | None = None,
    ) -> "ReviewWorkbench":
        sandbox = tempfile.TemporaryDirectory(prefix="minchoagnt-workbench-")
        workbench = cls(
            sandbox.name,
            reviewer_type=reviewer_type,
            review_engine=review_engine,
            reviewer_config=reviewer_config,
        )
        workbench._sandbox = sandbox
        return workbench

    def close(self) -> None:
        if self._sandbox is not None:
            self._sandbox.cleanup()
            self._sandbox = None

    def review(self, user_text: str) -> WorkbenchRun:
        self._run_count += 1
        run_id = f"run_{self._run_count:03d}"
        message = Message(
            id=1,
            session_id=run_id,
            role="user",
            content=user_text,
            timestamp=0.0,
        )
        events = [
            WorkbenchEvent("input", "success", "input received"),
            WorkbenchEvent("reviewer", "success", "reviewer selected"),
            WorkbenchEvent("review", "running", "review started"),
        ]
        plan = self.review_engine.review([message], review_memory=True, review_skills=True)
        events.append(WorkbenchEvent("review", "success", "review completed"))
        reviewer_config = dict(self.reviewer_config)
        last_error = getattr(self.review_engine, "last_error", None)
        if last_error:
            reviewer_config["last_error"] = str(last_error)
        return WorkbenchRun(
            run_id=run_id,
            input=WorkbenchInput(role="user", content=user_text),
            reviewer=WorkbenchReviewer(
                type=self.reviewer_type,
                config=reviewer_config,
            ),
            review_plan=plan,
            events=events,
            node_status={
                "UserMessage": "success",
                "ReviewEngine": "success",
                "ReviewPlan": "no-op" if _plan_is_empty(plan) else "success",
                "StateDiff": "pending",
            },
        )

    def apply(self, run: WorkbenchRun) -> WorkbenchRun:
        events = list(run.events)
        events.append(WorkbenchEvent("apply", "running", "apply started"))
        before_memory = self._memory_entries()
        before_skills = self._skill_names()

        memory_saved = 0
        memory_duplicates = 0
        memory_failed = 0
        skills_created = 0
        skill_duplicates = 0
        skill_failed = 0
        errors: list[str] = []

        memory = MemoryStore(self.home).load()
        for addition in run.review_plan.memory_additions:
            try:
                if memory.add(addition.target, addition.content):  # type: ignore[arg-type]
                    memory_saved += 1
                    events.append(
                        WorkbenchEvent("apply", "success", "memory addition saved")
                    )
                else:
                    memory_duplicates += 1
                    events.append(
                        WorkbenchEvent("apply", "no-op", "memory addition duplicate")
                    )
            except (ValueError, MemoryErrorBase) as exc:
                memory_failed += 1
                errors.append(str(exc))
                events.append(WorkbenchEvent("apply", "error", "memory addition rejected"))

        skills = SkillStore(self.home)
        for creation in run.review_plan.skill_creations:
            try:
                skills.create(creation.name, creation.content, category=creation.category)
                skills_created += 1
                events.append(WorkbenchEvent("apply", "success", "skill creation saved"))
            except SkillExistsError:
                skill_duplicates += 1
                events.append(WorkbenchEvent("apply", "no-op", "skill creation duplicate"))
            except (ValueError, SkillError) as exc:
                skill_failed += 1
                errors.append(str(exc))
                events.append(WorkbenchEvent("apply", "error", "skill creation rejected"))

        result = ApplyResult(
            memory_saved=memory_saved,
            memory_duplicates=memory_duplicates,
            memory_failed=memory_failed,
            skills_created=skills_created,
            skill_duplicates=skill_duplicates,
            skill_failed=skill_failed,
            empty_plan=_plan_is_empty(run.review_plan),
            errors=errors,
        )
        after_memory = self._memory_entries()
        after_skills = self._skill_names()
        diff = WorkbenchDiff(
            memory=_list_diff(before_memory["memory"], after_memory["memory"]),
            user=_list_diff(before_memory["user"], after_memory["user"]),
            skills=SkillDiff(
                created=_added(before_skills, after_skills),
                unchanged=_unchanged(before_skills, after_skills),
            ),
        )
        state_status = _state_status(result)
        events.append(WorkbenchEvent("apply", state_status, "apply completed"))
        return replace(
            run,
            apply_result=result,
            diff=diff,
            events=events,
            node_status={
                **run.node_status,
                "StateDiff": state_status,
            },
        )

    def expect(self, run: WorkbenchRun, target: str, contains: str) -> WorkbenchRun:
        target = target.strip()
        needle = contains.strip()
        if target not in {"user", "memory", "skills", "review_plan"}:
            raise ValueError("target must be user, memory, skills, or review_plan.")
        if not needle:
            raise ValueError("contains cannot be empty.")
        haystack = _expectation_values(run, target)
        passed = any(needle in value for value in haystack)
        target_label = _target_label(target)
        message = (
            f"matched {target_label}"
            if passed
            else f"no match in {target_label}"
        )
        result = CheckResult(
            target=target,
            contains=needle,
            passed=passed,
            message=message,
        )
        events = list(run.events)
        events.append(
            WorkbenchEvent(
                "expect",
                "success" if passed else "no-op",
                "? verify passed" if passed else "? verify failed",
            )
        )
        return replace(run, check_result=result, events=events)

    @staticmethod
    def _reviewer_for(reviewer_type: str, config: dict[str, Any]) -> ReviewEngine:
        if reviewer_type == "regex":
            return RegexReviewEngine()
        if reviewer_type == "fake":
            return FakeReviewEngine()
        if reviewer_type == "ollama":
            return OllamaReviewEngine(
                model=str(config.get("model", "qwen2.5:7b")),
                base_url=str(config.get("base_url", "http://127.0.0.1:11434")),
                timeout_seconds=float(config.get("timeout_seconds", 30)),
            )
        raise ValueError("reviewer_type must be 'regex', 'fake', or 'ollama'.")

    def _memory_entries(self) -> dict[str, list[str]]:
        memory = MemoryStore(self.home).load()
        return {
            "memory": memory.entries("memory"),
            "user": memory.entries("user"),
        }

    def _skill_names(self) -> list[str]:
        return SkillStore(self.home).list_names()


def _plan_is_empty(plan: ReviewPlan) -> bool:
    return not plan.memory_additions and not plan.skill_creations


def _list_diff(before: list[str], after: list[str]) -> ListDiff:
    return ListDiff(
        added=_added(before, after),
        removed=[entry for entry in before if entry not in after],
        unchanged=_unchanged(before, after),
    )


def _added(before: list[str], after: list[str]) -> list[str]:
    return [entry for entry in after if entry not in before]


def _unchanged(before: list[str], after: list[str]) -> list[str]:
    return [entry for entry in after if entry in before]


def _state_status(result: ApplyResult) -> NodeStatus:
    if result.memory_failed or result.skill_failed:
        return "error"
    if result.memory_saved or result.skills_created:
        return "success"
    return "no-op"


def _expectation_values(run: WorkbenchRun, target: str) -> list[str]:
    if target == "user":
        return run.diff.user.added + run.diff.user.unchanged
    if target == "memory":
        return run.diff.memory.added + run.diff.memory.unchanged
    if target == "skills":
        return run.diff.skills.created + run.diff.skills.unchanged
    return [run.review_plan.to_json()]


def _target_label(target: str) -> str:
    if target == "user":
        return "user memory"
    if target == "memory":
        return "memory"
    if target == "skills":
        return "skills"
    return "review plan"
