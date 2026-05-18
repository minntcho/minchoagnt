from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


class SkillError(Exception):
    """Base class for skill store errors."""


class SkillExistsError(SkillError):
    """Raised when creating a skill that already exists."""


class SkillMatchError(SkillError):
    """Raised when a patch target is missing or ambiguous."""


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    category: str | None = None
    description: str = ""


class SkillStore:
    """File-backed procedural memory stored as SKILL.md documents."""

    def __init__(self, home: Path | str):
        self.home = Path(home)
        self.skills_dir = self.home / "skills"

    def create(self, name: str, content: str, category: str | None = None) -> Skill:
        slug = self._slug(name)
        if self._find_path(slug):
            raise SkillExistsError(f"Skill {slug!r} already exists.")
        skill_dir = self._directory_for(slug, category)
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        self._atomic_write(path, content.strip() + "\n")
        return self._skill_from_path(path)

    def list_names(self) -> list[str]:
        if not self.skills_dir.exists():
            return []
        names = [path.parent.name for path in self.skills_dir.rglob("SKILL.md")]
        return sorted(dict.fromkeys(names))

    def view(self, name: str) -> str:
        path = self._require_path(name)
        return path.read_text(encoding="utf-8")

    def patch(self, name: str, old_string: str, new_string: str) -> None:
        path = self._require_path(name)
        content = path.read_text(encoding="utf-8")
        count = content.count(old_string)
        if count != 1:
            raise SkillMatchError(
                f"Expected one match for {old_string!r} in {name!r}, found {count}."
            )
        self._atomic_write(path, content.replace(old_string, new_string, 1))

    def _directory_for(self, slug: str, category: str | None) -> Path:
        if category:
            return self.skills_dir / self._slug(category) / slug
        return self.skills_dir / slug

    def _require_path(self, name: str) -> Path:
        path = self._find_path(self._slug(name))
        if path is None:
            raise FileNotFoundError(f"Skill {name!r} does not exist.")
        return path

    def _find_path(self, slug: str) -> Path | None:
        direct = self.skills_dir / slug / "SKILL.md"
        if direct.exists():
            return direct
        if not self.skills_dir.exists():
            return None
        for path in self.skills_dir.rglob("SKILL.md"):
            if path.parent.name == slug:
                return path
        return None

    def _skill_from_path(self, path: Path) -> Skill:
        category = None
        try:
            relative = path.parent.relative_to(self.skills_dir)
            if len(relative.parts) > 1:
                category = relative.parts[0]
        except ValueError:
            category = None
        return Skill(
            name=path.parent.name,
            path=path,
            category=category,
            description=self._description(path.read_text(encoding="utf-8")),
        )

    @staticmethod
    def _description(content: str) -> str:
        match = re.search(r"^description:\s*(.+)$", content, flags=re.MULTILINE)
        return match.group(1).strip().strip('"') if match else ""

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
        if not slug:
            raise ValueError("Skill name cannot be empty.")
        return slug

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".skill-", suffix=".tmp", dir=path.parent)
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
