# Review Workbench Ollama Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ollama as an optional Review Workbench reviewer without making normal tests depend on a local model.

**Architecture:** Extend the Workbench HTTP API to accept Ollama settings and create `OllamaReviewEngine` only when requested. Keep regex/fake as deterministic defaults, and surface Ollama errors through the existing empty-plan/no-op behavior plus reviewer detail metadata.

**Tech Stack:** Python stdlib HTTP server, existing `OllamaReviewEngine`, vanilla HTML/JS, `unittest`.

---

## File Structure

- Modify `minchoagnt/workbench.py`
  - Add `ollama` reviewer construction.
  - Add optional reviewer config in `WorkbenchReviewer`.
- Modify `minchoagnt/web.py`
  - Accept `model`, `base_url`, and `timeout` in `/api/review`.
  - Add Ollama controls to the UI.
- Modify `tests/test_web.py`
  - Test API wiring with a patched fake OllamaReviewEngine.
  - Test invalid Ollama config validation.
- Modify `tests/test_workbench.py`
  - Test Workbench reviewer metadata for injected reviewer config.
- Modify `README.md`
  - Add an Ollama workbench launch/use note.

### Task 1: API Wiring Test

- [ ] Write a failing test that patches `minchoagnt.web.OllamaReviewEngine`, posts `reviewer=ollama`, and asserts the engine receives model/base URL/timeout.
- [ ] Run the test and verify it fails because `/api/review` only accepts regex/fake.
- [ ] Implement Ollama route handling and engine construction.
- [ ] Run the focused test and verify it passes.

### Task 2: UI Controls

- [ ] Add model/base URL/timeout fields that appear in the command builder.
- [ ] Include those settings in the `/api/review` payload.
- [ ] Keep regex/fake unchanged.
- [ ] Smoke test in the browser with fake or unavailable Ollama and verify the UI stays responsive.

### Task 3: Verification And PR

- [ ] Run `python -m unittest tests.test_web -v`.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `git diff --check`.
- [ ] Commit, push, and open a draft PR.

## Self-review

- Spec coverage: adds optional Ollama reviewer selection while preserving deterministic default tests.
- Intentional gaps: no real local model integration test, no model discovery, and no streaming.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: API payload fields are `reviewer`, `model`, `base_url`, and `timeout`.
