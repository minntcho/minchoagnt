# Review Workbench Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal local web frontend for the Review Workbench backend.

**Architecture:** Add a stdlib HTTP server in `minchoagnt.web` that serves one embedded HTML/CSS/JS page and JSON API endpoints backed by `ReviewWorkbench.sandbox()`. Add a CLI command that starts the local workbench server without adding new runtime dependencies.

**Tech Stack:** Python stdlib `http.server`, existing `ReviewWorkbench`, vanilla HTML/CSS/JS, `unittest`.

---

## File Structure

- Create `minchoagnt/web.py`
  - Owns the HTTP handler, embedded UI, API request parsing, and server startup helper.
- Modify `minchoagnt/cli.py`
  - Adds `python -m minchoagnt workbench --host 127.0.0.1 --port 0`.
- Create `tests/test_web.py`
  - Tests root HTML response.
  - Tests review/apply API flow through a real local HTTP server.
  - Tests malformed JSON behavior.
- Modify `README.md`
  - Adds a short command for launching the workbench.

### Task 1: HTML Response And Handler Factory

**Files:**
- Create: `tests/test_web.py`
- Create: `minchoagnt/web.py`

- [ ] **Step 1: Write the failing HTML test**

```python
import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer

from minchoagnt.web import create_workbench_handler


class WebServerContext:
    def __enter__(self):
        handler = create_workbench_handler()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response, data


class ReviewWorkbenchWebTests(unittest.TestCase):
    def test_root_serves_workbench_html(self):
        with WebServerContext() as server:
            response, data = server.request("GET", "/")

        html = data.decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("Review Workbench", html)
        self.assertIn("~ Review", html)
        self.assertIn("! Apply", html)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m unittest tests.test_web.ReviewWorkbenchWebTests.test_root_serves_workbench_html -v
```

Expected: fail because `minchoagnt.web` does not exist.

- [ ] **Step 3: Implement the minimal handler**

Create `create_workbench_handler()` and serve `WORKBENCH_HTML` for `GET /`.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m unittest tests.test_web.ReviewWorkbenchWebTests.test_root_serves_workbench_html -v
```

Expected: pass.

### Task 2: Review And Apply API

**Files:**
- Modify: `tests/test_web.py`
- Modify: `minchoagnt/web.py`

- [ ] **Step 1: Write the failing API test**

Add a test that posts `{"message":"remember: I prefer Korean summaries.","reviewer":"regex"}` to `/api/review`, checks the returned `run_id`, then posts the same `run_id` to `/api/apply` and checks `apply_result.memory_saved == 1`.

- [ ] **Step 2: Run the API test to verify it fails**

Run:

```powershell
python -m unittest tests.test_web.ReviewWorkbenchWebTests.test_review_and_apply_api_flow -v
```

Expected: fail because API routes are missing.

- [ ] **Step 3: Implement API routes**

Add `POST /api/review` and `POST /api/apply`. Store runs in the handler class dictionary by `run_id`.

- [ ] **Step 4: Run the API test to verify it passes**

Run:

```powershell
python -m unittest tests.test_web.ReviewWorkbenchWebTests.test_review_and_apply_api_flow -v
```

Expected: pass.

### Task 3: CLI And Verification

**Files:**
- Modify: `minchoagnt/cli.py`
- Modify: `README.md`

- [ ] **Step 1: Add CLI command**

Add a `workbench` subcommand that calls `serve_workbench(host=args.host, port=args.port)`.

- [ ] **Step 2: Add README command**

Add:

```powershell
python -m minchoagnt workbench --host 127.0.0.1 --port 8000
```

- [ ] **Step 3: Run full tests**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 4: Browser smoke test**

Start the server on an available port, open it in the in-app browser, verify the page loads, submit a review message, apply it, and confirm the graph/detail/log update.

## Self-review

- Spec coverage: this plan adds the minimal frontend surface, review/apply controls, graph/detail/log rendering, and sandbox-backed API flow.
- Intentional gaps: Ollama reviewer, manual ReviewPlan editing, and explicit EXPECT/check builder remain future work.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: tests and implementation use `create_workbench_handler()` and `serve_workbench()`.
