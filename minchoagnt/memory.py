from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Target = Literal["memory", "user"]
ENTRY_DELIMITER = "\n§\n"


class MemoryErrorBase(Exception):
    """Base class for memory store errors."""


class MemoryLimitError(MemoryErrorBase):
    def __init__(self, message: str, current_entries: list[str]):
        super().__init__(message)
        self.current_entries = current_entries


class MemoryMatchError(MemoryErrorBase):
    """Raised when replace/remove cannot identify exactly one entry."""


@dataclass(frozen=True)
class MemoryUsage:
    target: Target
    chars: int
    limit: int
    entries: int


class MemoryStore:
    """Bounded file-backed memory with Hermes-style frozen snapshots."""

    def __init__(
        self,
        home: Path | str,
        memory_limit: int = 2200,
        user_limit: int = 1375,
    ):
        self.home = Path(home)
        self.memory_dir = self.home / "memories"
        self.memory_limit = memory_limit
        self.user_limit = user_limit
        self._entries: dict[Target, list[str]] = {"memory": [], "user": []}
        self._snapshot: dict[Target, str | None] = {"memory": None, "user": None}

    def load(self) -> "MemoryStore":
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._entries["memory"] = self._read_entries(self._path_for("memory"))
        self._entries["user"] = self._read_entries(self._path_for("user"))
        self._snapshot["memory"] = self._render_snapshot("memory")
        self._snapshot["user"] = self._render_snapshot("user")
        return self

    def entries(self, target: Target) -> list[str]:
        self._validate_target(target)
        return list(self._entries[target])

    def snapshot(self, target: Target) -> str | None:
        self._validate_target(target)
        return self._snapshot[target]

    def usage(self, target: Target) -> MemoryUsage:
        self._validate_target(target)
        return MemoryUsage(
            target=target,
            chars=self._char_count(target),
            limit=self._limit_for(target),
            entries=len(self._entries[target]),
        )

    def add(self, target: Target, content: str) -> bool:
        self._validate_target(target)
        entry = self._clean(content)
        if entry in self._entries[target]:
            return False
        proposed = self._entries[target] + [entry]
        self._ensure_within_limit(target, proposed)
        self._entries[target] = proposed
        self._save(target)
        return True

    def replace(self, target: Target, old_text: str, content: str) -> None:
        self._validate_target(target)
        old = self._clean(old_text)
        new_entry = self._clean(content)
        index = self._unique_match_index(target, old)
        proposed = list(self._entries[target])
        proposed[index] = new_entry
        self._ensure_within_limit(target, proposed)
        self._entries[target] = proposed
        self._save(target)

    def remove(self, target: Target, old_text: str) -> None:
        self._validate_target(target)
        old = self._clean(old_text)
        index = self._unique_match_index(target, old)
        entries = list(self._entries[target])
        entries.pop(index)
        self._entries[target] = entries
        self._save(target)

    def _unique_match_index(self, target: Target, old_text: str) -> int:
        matches = [i for i, entry in enumerate(self._entries[target]) if old_text in entry]
        if len(matches) != 1:
            raise MemoryMatchError(
                f"Expected one memory entry to match {old_text!r}, found {len(matches)}."
            )
        return matches[0]

    def _save(self, target: Target) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._atomic_write(self._path_for(target), ENTRY_DELIMITER.join(self._entries[target]))

    def _ensure_within_limit(self, target: Target, entries: list[str]) -> None:
        total = len(ENTRY_DELIMITER.join(entries))
        limit = self._limit_for(target)
        if total > limit:
            raise MemoryLimitError(
                f"{target} memory would be {total}/{limit} chars.",
                current_entries=list(self._entries[target]),
            )

    def _render_snapshot(self, target: Target) -> str | None:
        entries = self._entries[target]
        if not entries:
            return None
        usage = self.usage(target)
        label = "USER PROFILE" if target == "user" else "MEMORY"
        bar = "=" * 46
        body = ENTRY_DELIMITER.join(entries)
        return f"{bar}\n{label} [{usage.chars}/{usage.limit} chars]\n{bar}\n{body}"

    def _path_for(self, target: Target) -> Path:
        filename = "USER.md" if target == "user" else "MEMORY.md"
        return self.memory_dir / filename

    def _limit_for(self, target: Target) -> int:
        return self.user_limit if target == "user" else self.memory_limit

    def _char_count(self, target: Target) -> int:
        return len(ENTRY_DELIMITER.join(self._entries[target]))

    @staticmethod
    def _read_entries(path: Path) -> list[str]:
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
        entries = [entry.strip() for entry in raw.split(ENTRY_DELIMITER)]
        return list(dict.fromkeys(entry for entry in entries if entry))

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".memory-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    @staticmethod
    def _clean(value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Memory content cannot be empty.")
        return cleaned

    @staticmethod
    def _validate_target(target: str) -> None:
        if target not in {"memory", "user"}:
            raise ValueError("target must be 'memory' or 'user'.")
