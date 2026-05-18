import tempfile
import unittest
from pathlib import Path

from minchoagnt.memory import MemoryStore
from minchoagnt.skills import SkillStore
from minchoagnt.workbench import ReviewWorkbench


class ReviewWorkbenchTests(unittest.TestCase):
    def test_review_returns_renderable_run_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            workbench = ReviewWorkbench(Path(tmp), reviewer_type="regex")

            run = workbench.review("remember: I prefer Korean summaries.")

            self.assertEqual(run.run_id, "run_001")
            self.assertEqual(run.input.role, "user")
            self.assertEqual(run.input.content, "remember: I prefer Korean summaries.")
            self.assertEqual(run.reviewer.type, "regex")
            self.assertEqual(
                run.review_plan.to_dict()["memory_additions"],
                [{"target": "user", "content": "I prefer Korean summaries."}],
            )
            self.assertEqual(run.apply_result.memory_saved, 0)
            self.assertEqual(run.node_status["StateDiff"], "pending")
            self.assertEqual(run.to_dict()["reviewer"], {"type": "regex"})
            self.assertIn("review completed", [event.message for event in run.events])

    def test_apply_writes_memory_and_reports_state_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workbench = ReviewWorkbench(home, reviewer_type="regex")
            run = workbench.review("remember: I prefer Korean summaries.")

            applied = workbench.apply(run)

            self.assertEqual(applied.apply_result.memory_saved, 1)
            self.assertEqual(applied.diff.user.added, ["I prefer Korean summaries."])
            self.assertEqual(applied.diff.user.removed, [])
            self.assertEqual(applied.diff.skills.created, [])
            self.assertEqual(applied.node_status["StateDiff"], "success")
            self.assertIn("memory addition saved", [event.message for event in applied.events])

    def test_apply_reports_duplicate_memory_as_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            memory = MemoryStore(home).load()
            memory.add("user", "I prefer Korean summaries.")
            workbench = ReviewWorkbench(home, reviewer_type="regex")
            run = workbench.review("remember: I prefer Korean summaries.")

            applied = workbench.apply(run)

            self.assertEqual(applied.apply_result.memory_saved, 0)
            self.assertEqual(applied.apply_result.memory_duplicates, 1)
            self.assertEqual(applied.apply_result.errors, [])
            self.assertEqual(applied.diff.user.added, [])
            self.assertEqual(applied.diff.user.unchanged, ["I prefer Korean summaries."])
            self.assertEqual(applied.node_status["StateDiff"], "no-op")

    def test_apply_creates_skill_and_reports_skill_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workbench = ReviewWorkbench(home, reviewer_type="regex")
            run = workbench.review(
                "skill: release-checklist | run tests; inspect git status; push branch"
            )

            applied = workbench.apply(run)

            self.assertEqual(applied.apply_result.skills_created, 1)
            self.assertEqual(applied.diff.skills.created, ["release-checklist"])
            self.assertEqual(applied.node_status["StateDiff"], "success")
            self.assertIn("inspect git status", SkillStore(home).view("release-checklist"))

    def test_apply_reports_duplicate_skill_as_noop_without_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workbench = ReviewWorkbench(home, reviewer_type="regex")
            run = workbench.review("skill: release-checklist | run tests")
            workbench.apply(run)

            duplicate = workbench.apply(run)

            self.assertEqual(duplicate.apply_result.skills_created, 0)
            self.assertEqual(duplicate.apply_result.skill_duplicates, 1)
            self.assertEqual(duplicate.apply_result.errors, [])
            self.assertEqual(duplicate.diff.skills.created, [])
            self.assertEqual(duplicate.diff.skills.unchanged, ["release-checklist"])
            self.assertEqual(duplicate.node_status["StateDiff"], "no-op")

    def test_empty_plan_apply_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            workbench = ReviewWorkbench(Path(tmp), reviewer_type="regex")
            run = workbench.review("hello there")

            applied = workbench.apply(run)

            self.assertTrue(applied.apply_result.empty_plan)
            self.assertEqual(applied.apply_result.memory_saved, 0)
            self.assertEqual(applied.apply_result.skills_created, 0)
            self.assertEqual(applied.node_status["StateDiff"], "no-op")

    def test_fake_reviewer_produces_empty_plan_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            workbench = ReviewWorkbench(Path(tmp), reviewer_type="fake")

            run = workbench.review("remember: I prefer Korean summaries.")

            self.assertEqual(run.review_plan.to_dict()["memory_additions"], [])
            self.assertEqual(run.node_status["ReviewPlan"], "no-op")


if __name__ == "__main__":
    unittest.main()
