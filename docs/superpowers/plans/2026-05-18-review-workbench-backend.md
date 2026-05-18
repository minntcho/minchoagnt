# Review Workbench Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic backend slice that turns one user message into a ReviewPlan, applies it to sandbox memory/skills, and returns a renderable StateDiff run object.

**Architecture:** Add a focused `minchoagnt.workbench` module that composes the existing `ReviewEngine`, `MemoryStore`, and `SkillStore` APIs. Keep `MiniAgent` unchanged so the workbench can evolve as a frontend/testing surface without changing the CLI chat loop.

**Tech Stack:** Python stdlib, dataclasses, existing minchoagnt stores and review schema, `unittest`.

---

## File Structure

- Create `minchoagnt/workbench.py`
  - Defines workbench result dataclasses.
  - Defines a small fake reviewer for deterministic UI/test demos.
  - Defines `ReviewWorkbench.review()` and `ReviewWorkbench.apply()`.
- Create `tests/test_workbench.py`
  - Tests review-only run objects.
  - Tests sandbox apply diffs.
  - Tests duplicate/no-op behavior.
  - Tests skill creation diffs.
  - Tests empty-plan no-op behavior.
- Modify `minchoagnt/__init__.py`
  - Export the public workbench classes.

### Task 1: Review Run Model

**Files:**
- Create: `tests/test_workbench.py`
- Create: `minchoagnt/workbench.py`
- Modify: `minchoagnt/__init__.py`

- [ ] **Step 1: Write the failing review test**

Add this test to `tests/test_workbench.py`:

```python
import tempfile
import unittest
from pathlib import Path

from minchoagnt.workbench import ReviewWorkbench


class ReviewWorkbenchTests(unittest.TestCase):
    def test_review_returns_renderable_run_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            workbench = ReviewWorkbench(Path(tmp), reviewer_type="regex")

            run = workbench.review("remember: I prefer Korean summaries.")

            self.assertEqual(run.run_id, "run_001")
            self.assertEqual(run.input.role, "user")
            self.assertEqual(run.reviewer.type, "regex")
            self.assertEqual(
                run.review_plan.to_dict()["memory_additions"],
                [{"target": "user", "content": "I prefer Korean summaries."}],
            )
            self.assertEqual(run.apply_result.memory_saved, 0)
            self.assertEqual(run.node_status["StateDiff"], "pending")
            self.assertEqual(run.to_dict()["reviewer"], {"type": "regex"})
            self.assertIn("review completed", [event.message for event in run.events])
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m unittest tests.test_workbench.ReviewWorkbenchTests.test_review_returns_renderable_run_object -v
```

Expected: fail because `minchoagnt.workbench` does not exist.

- [ ] **Step 3: Implement the minimal review model**

Create `minchoagnt/workbench.py` with dataclasses for `WorkbenchInput`,
`WorkbenchReviewer`, `WorkbenchEvent`, `ApplyResult`, `ListDiff`, `SkillDiff`,
`WorkbenchDiff`, `WorkbenchRun`, and `ReviewWorkbench.review()`. Export
`ReviewWorkbench` from `minchoagnt/__init__.py`.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m unittest tests.test_workbench.ReviewWorkbenchTests.test_review_returns_renderable_run_object -v
```

Expected: pass.

### Task 2: Sandbox Apply And Diffs

**Files:**
- Modify: `tests/test_workbench.py`
- Modify: `minchoagnt/workbench.py`

- [ ] **Step 1: Write the failing apply test**

Add this test:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m unittest tests.test_workbench.ReviewWorkbenchTests.test_apply_writes_memory_and_reports_state_diff -v
```

Expected: fail because `ReviewWorkbench.apply()` is not implemented.

- [ ] **Step 3: Implement minimal apply**

Load `MemoryStore` and `SkillStore` from the workbench home, capture before/after
entries, apply each candidate, and build `WorkbenchDiff`.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m unittest tests.test_workbench.ReviewWorkbenchTests.test_apply_writes_memory_and_reports_state_diff -v
```

Expected: pass.

### Task 3: No-op And Skill Results

**Files:**
- Modify: `tests/test_workbench.py`
- Modify: `minchoagnt/workbench.py`

- [ ] **Step 1: Write failing duplicate, skill, and empty-plan tests**

Add tests for duplicate memory, skill creation, and empty plan behavior.

- [ ] **Step 2: Run the new focused tests to verify they fail**

Run:

```powershell
python -m unittest tests.test_workbench -v
```

Expected: new tests fail until apply result counts and node status are completed.

- [ ] **Step 3: Complete result accounting**

Track `memory_duplicates`, `memory_failed`, `skills_created`,
`skill_duplicates`, `skill_failed`, and `empty_plan`. Mark `StateDiff` as
`no-op` when the plan is empty or all candidates are duplicates.

- [ ] **Step 4: Run workbench tests**

Run:

```powershell
python -m unittest tests.test_workbench -v
```

Expected: pass.

### Task 4: Package Verification

**Files:**
- Modify: `minchoagnt/__init__.py`

- [ ] **Step 1: Export workbench classes**

Ensure callers can import:

```python
from minchoagnt import ReviewWorkbench
```

- [ ] **Step 2: Run the full test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

Run:

```powershell
git add minchoagnt/workbench.py minchoagnt/__init__.py tests/test_workbench.py docs/superpowers/plans/2026-05-18-review-workbench-backend.md
git commit -m "feat: add review workbench backend"
```

## Self-review

- Spec coverage: this plan covers run object creation, deterministic reviewer support, sandbox/home-based apply, StateDiff rendering data, event logs, duplicates, empty plan handling, and package export.
- Intentional gaps: browser UI, Ollama reviewer option, manual ReviewPlan editing, and explicit EXPECT/check builder remain future work.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: all task references use `ReviewWorkbench`, `WorkbenchRun`, `ApplyResult`, and `WorkbenchDiff`.
