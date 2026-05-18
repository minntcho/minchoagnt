# Review Workbench EXPECT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small explicit `? Verify` check builder to the Review Workbench.

**Architecture:** Extend `WorkbenchRun` with one optional check result and add `ReviewWorkbench.expect()` for deterministic contains checks against ReviewPlan, memory diff, user diff, or skill diff. Expose it through `/api/expect` and a minimal UI with target and text inputs.

**Tech Stack:** Python stdlib HTTP server, existing `ReviewWorkbench`, vanilla HTML/JS, `unittest`.

---

## File Structure

- Modify `minchoagnt/workbench.py`
  - Add `CheckResult`.
  - Add `ReviewWorkbench.expect(run, target, contains)`.
  - Include check result in `WorkbenchRun.to_dict()`.
- Modify `minchoagnt/web.py`
  - Add `/api/expect`.
  - Add `? Verify` target/text controls and button.
- Modify `tests/test_workbench.py`
  - Test passing user-memory expectation after apply.
  - Test failing expectation when text is absent.
- Modify `tests/test_web.py`
  - Test review/apply/expect HTTP flow.
- Modify `README.md`
  - Mention the workbench can run simple contains checks.

### Task 1: Workbench Check Model

- [ ] Write failing tests for `ReviewWorkbench.expect()`.
- [ ] Implement `CheckResult` and deterministic target lookup.
- [ ] Run focused workbench tests.

### Task 2: Web API And UI

- [ ] Write failing `/api/expect` test.
- [ ] Implement API route and payload validation.
- [ ] Add target/text controls and `? Verify` button to the UI.
- [ ] Run focused web tests.

### Task 3: Verification And PR

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `git diff --check`.
- [ ] Browser smoke test Review -> Apply -> Verify.
- [ ] Commit, push, and open a draft PR.

## Self-review

- Spec coverage: this adds the first explicit check builder without inventing a full expression language.
- Intentional gaps: no boolean expressions, no multiple assertions, no custom operators beyond contains.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: API payload fields are `run_id`, `target`, and `contains`.
