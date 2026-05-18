import tempfile
import unittest
from pathlib import Path

from minchoagnt.skills import SkillMatchError, SkillStore


class SkillStoreTests(unittest.TestCase):
    def test_create_list_view_and_patch_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SkillStore(Path(tmp))
            content = """---
name: release-checklist
description: Repeatable release verification.
---

# Release Checklist

1. Run tests.
2. Check git status.
"""

            skill = store.create("release-checklist", content, category="dev")

            self.assertEqual(skill.name, "release-checklist")
            self.assertEqual(store.list_names(), ["release-checklist"])
            self.assertIn("Run tests.", store.view("release-checklist"))

            store.patch("release-checklist", "Run tests.", "Run the full test suite.")

            self.assertIn("Run the full test suite.", store.view("release-checklist"))

    def test_patch_rejects_ambiguous_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SkillStore(Path(tmp))
            store.create(
                "ambiguous",
                "# Ambiguous\n\nRun tests.\nRun tests again.\n",
            )

            with self.assertRaises(SkillMatchError):
                store.patch("ambiguous", "Run tests", "Run focused tests")


if __name__ == "__main__":
    unittest.main()
