import tempfile
import unittest
from pathlib import Path

from minchoagnt.agent import MiniAgent
from minchoagnt.memory import MemoryStore
from minchoagnt.skills import SkillStore


class MiniAgentReviewTests(unittest.TestCase):
    def test_memory_review_runs_after_configured_user_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agent = MiniAgent(home, memory_interval=2, skill_interval=99)

            first = agent.chat("remember: I prefer Korean summaries.")
            self.assertFalse(first.review.memory_saved)

            second = agent.chat("hello again")
            self.assertEqual(second.review.memory_saved, 1)

            memory = MemoryStore(home)
            memory.load()
            self.assertEqual(memory.entries("user"), ["I prefer Korean summaries."])

    def test_skill_review_creates_skill_after_tool_iteration_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agent = MiniAgent(home, memory_interval=99, skill_interval=3)

            result = agent.chat(
                "skill: release-checklist | run tests; inspect git status; push branch",
                tool_iterations=3,
            )

            self.assertEqual(result.review.skills_created, 1)

            skills = SkillStore(home)
            self.assertEqual(skills.list_names(), ["release-checklist"])
            self.assertIn("inspect git status", skills.view("release-checklist"))

    def test_context_includes_memory_snapshot_and_skill_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            memory = MemoryStore(home)
            memory.load()
            memory.add("memory", "Project conventions live in AGENTS.md.")
            SkillStore(home).create("repo-review", "# Repo Review\n\nRead the tree first.")

            agent = MiniAgent(home)

            context = agent.context()

            self.assertIn("MEMORY", context)
            self.assertIn("Project conventions", context)
            self.assertIn("Available skills", context)
            self.assertIn("repo-review", context)


if __name__ == "__main__":
    unittest.main()
