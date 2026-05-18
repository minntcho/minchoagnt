from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from minchoagnt.ollama import OllamaReviewEngine
from minchoagnt.workbench import ReviewWorkbench, WorkbenchRun


WORKBENCH_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Review Workbench</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #18202a;
      --muted: #667085;
      --line: #d7dce3;
      --accent: #0d766e;
      --accent-dark: #0a5f59;
      --warn: #9a6700;
      --error: #b42318;
      --ok: #067647;
      --idle: #667085;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
    }
    button, input, textarea, select {
      font: inherit;
    }
    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr minmax(112px, 22vh);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }
    h1 {
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .status {
      min-width: 128px;
      text-align: right;
      color: var(--muted);
      font-size: 13px;
    }
    main {
      display: grid;
      grid-template-columns: minmax(260px, 360px) minmax(360px, 1fr) minmax(320px, 460px);
      min-height: 0;
    }
    section {
      min-width: 0;
      min-height: 0;
      padding: 16px;
      border-right: 1px solid var(--line);
    }
    section:last-child { border-right: 0; }
    .section-title {
      margin: 0 0 12px;
      font-size: 13px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .08em;
    }
    .builder {
      display: grid;
      grid-template-rows: auto auto auto 1fr;
      gap: 14px;
      background: var(--panel);
    }
    label {
      display: block;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    textarea {
      width: 100%;
      min-height: 136px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      color: var(--ink);
      background: #fff;
    }
    input, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      color: var(--ink);
      background: #fff;
    }
    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    button {
      border: 1px solid transparent;
      border-radius: 8px;
      padding: 10px 12px;
      color: #fff;
      background: var(--accent);
      cursor: pointer;
      min-height: 42px;
    }
    button:hover { background: var(--accent-dark); }
    button:disabled {
      cursor: not-allowed;
      color: #98a2b3;
      border-color: var(--line);
      background: #eef1f5;
    }
    .target {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      background: #fbfcfd;
      font-size: 13px;
    }
    .graph {
      display: grid;
      align-content: start;
      gap: 12px;
    }
    .flow {
      display: grid;
      grid-template-columns: repeat(4, minmax(116px, 1fr));
      gap: 10px;
      align-items: stretch;
    }
    .node {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 12px;
      text-align: left;
      min-height: 96px;
      color: var(--ink);
    }
    .node strong {
      display: block;
      font-size: 14px;
      margin-bottom: 8px;
    }
    .node span {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      color: #fff;
      background: var(--idle);
    }
    .node[data-status="success"] span { background: var(--ok); }
    .node[data-status="running"] span { background: var(--accent); }
    .node[data-status="no-op"] span { background: var(--warn); }
    .node[data-status="error"] span { background: var(--error); }
    .node.selected {
      border-color: var(--accent);
      outline: 2px solid rgba(13, 118, 110, .16);
    }
    .operation {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .operation div {
      min-height: 64px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 10px;
      color: var(--muted);
      font-size: 13px;
    }
    .operation strong {
      display: block;
      color: var(--ink);
      font-size: 16px;
      margin-bottom: 4px;
    }
    .detail {
      background: var(--panel);
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      min-height: 360px;
      max-height: calc(100vh - 240px);
      background: #101828;
      color: #eef4ff;
      font-size: 12px;
      line-height: 1.55;
    }
    footer {
      min-height: 0;
      border-top: 1px solid var(--line);
      background: #ffffff;
      padding: 12px 16px;
      overflow: auto;
    }
    .log {
      display: grid;
      gap: 6px;
      margin: 0;
      padding: 0;
      list-style: none;
      font-size: 13px;
    }
    .log li {
      display: grid;
      grid-template-columns: 96px 92px 1fr;
      gap: 10px;
      align-items: start;
      color: var(--muted);
    }
    @media (max-width: 980px) {
      main {
        grid-template-columns: 1fr;
      }
      section {
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }
      .flow {
        grid-template-columns: 1fr 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <h1>Review Workbench</h1>
      <div class="status" id="status">Sandbox</div>
    </header>
    <main>
      <section class="builder">
        <h2 class="section-title">Command Builder</h2>
        <div>
          <label for="message">UserMessage</label>
          <textarea id="message">remember: I prefer Korean summaries.</textarea>
        </div>
        <div>
          <label for="reviewer">Reviewer @ Target</label>
          <select id="reviewer">
            <option value="regex">regex</option>
            <option value="fake">fake</option>
            <option value="ollama">ollama</option>
          </select>
        </div>
        <div>
          <label for="model">Ollama Model</label>
          <input id="model" value="qwen2.5:7b">
        </div>
        <div>
          <label for="base-url">Ollama Base URL</label>
          <input id="base-url" value="http://127.0.0.1:11434">
        </div>
        <div>
          <label for="timeout">Ollama Timeout</label>
          <input id="timeout" type="number" min="0.1" step="0.1" value="30">
        </div>
        <div class="actions">
          <button id="review">~ Review</button>
          <button id="apply" disabled>! Apply</button>
        </div>
        <div>
          <label for="expect-target">Expect Target</label>
          <select id="expect-target">
            <option value="user">user memory</option>
            <option value="memory">memory</option>
            <option value="skills">skills</option>
            <option value="review_plan">review plan</option>
          </select>
        </div>
        <div>
          <label for="expect-contains">Expect Contains</label>
          <input id="expect-contains" value="Korean summaries">
        </div>
        <div class="actions">
          <button id="expect" disabled>? Verify</button>
        </div>
        <div class="target">
          <span>? Verify</span>
          <strong id="verify">pending</strong>
        </div>
      </section>
      <section class="graph">
        <h2 class="section-title">Review Graph</h2>
        <div class="flow" id="graph"></div>
        <div class="operation">
          <div><strong>~</strong>review input</div>
          <div><strong>!</strong>apply plan</div>
          <div><strong>?</strong>inspect diff</div>
        </div>
      </section>
      <section class="detail">
        <h2 class="section-title" id="detail-title">Detail</h2>
        <pre id="detail">{}</pre>
      </section>
    </main>
    <footer>
      <h2 class="section-title">Execution Log</h2>
      <ul class="log" id="log"></ul>
    </footer>
  </div>
  <script>
    const nodes = ["UserMessage", "ReviewEngine", "ReviewPlan", "StateDiff"];
    let currentRun = null;
    let selectedNode = "UserMessage";

    function setStatus(text) {
      document.getElementById("status").textContent = text;
    }

    function render(run) {
      currentRun = run;
      const graph = document.getElementById("graph");
      graph.innerHTML = "";
      nodes.forEach((name) => {
        const button = document.createElement("button");
        button.className = "node" + (selectedNode === name ? " selected" : "");
        button.dataset.status = run.node_status[name] || "pending";
        button.innerHTML = `<strong>${name}</strong><span>${run.node_status[name] || "pending"}</span>`;
        button.addEventListener("click", () => {
          selectedNode = name;
          render(currentRun);
        });
        graph.appendChild(button);
      });
      document.getElementById("apply").disabled = !run.run_id;
      document.getElementById("expect").disabled = !run.run_id;
      document.getElementById("verify").textContent = verifyLabel(run);
      document.getElementById("detail-title").textContent = selectedNode;
      document.getElementById("detail").textContent = JSON.stringify(detailFor(run, selectedNode), null, 2);
      const log = document.getElementById("log");
      log.innerHTML = "";
      run.events.forEach((event) => {
        const item = document.createElement("li");
        item.innerHTML = `<strong>${event.step}</strong><span>${event.status}</span><span>${event.message}</span>`;
        log.appendChild(item);
      });
    }

    function detailFor(run, node) {
      if (node === "UserMessage") return run.input;
      if (node === "ReviewEngine") return run.reviewer;
      if (node === "ReviewPlan") return run.review_plan;
      return { apply_result: run.apply_result, diff: run.diff, check_result: run.check_result };
    }

    function verifyLabel(run) {
      if (run.check_result && run.check_result.message !== "not run") {
        return run.check_result.passed ? "pass" : "fail";
      }
      return run.node_status.StateDiff || "pending";
    }

    async function postJSON(path, payload) {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "request failed");
      return data;
    }

    document.getElementById("review").addEventListener("click", async () => {
      try {
        setStatus("Reviewing");
        selectedNode = "ReviewPlan";
        const run = await postJSON("/api/review", {
          message: document.getElementById("message").value,
          reviewer: document.getElementById("reviewer").value,
          model: document.getElementById("model").value,
          base_url: document.getElementById("base-url").value,
          timeout: Number(document.getElementById("timeout").value),
        });
        render(run);
        setStatus("Review ready");
      } catch (error) {
        setStatus(error.message);
      }
    });

    document.getElementById("apply").addEventListener("click", async () => {
      if (!currentRun) return;
      try {
        setStatus("Applying");
        selectedNode = "StateDiff";
        const run = await postJSON("/api/apply", { run_id: currentRun.run_id });
        render(run);
        setStatus("Applied");
      } catch (error) {
        setStatus(error.message);
      }
    });

    document.getElementById("expect").addEventListener("click", async () => {
      if (!currentRun) return;
      try {
        setStatus("Verifying");
        selectedNode = "StateDiff";
        const run = await postJSON("/api/expect", {
          run_id: currentRun.run_id,
          target: document.getElementById("expect-target").value,
          contains: document.getElementById("expect-contains").value,
        });
        render(run);
        setStatus(run.check_result.passed ? "Verify passed" : "Verify failed");
      } catch (error) {
        setStatus(error.message);
      }
    });
  </script>
</body>
</html>
"""


class WorkbenchRequestHandler(BaseHTTPRequestHandler):
    workbench: ReviewWorkbench
    runs: dict[str, WorkbenchRun]

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send(HTTPStatus.OK, WORKBENCH_HTML, "text/html; charset=utf-8")
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            return

        if self.path == "/api/review":
            self._handle_review(payload)
            return
        if self.path == "/api/apply":
            self._handle_apply(payload)
            return
        if self.path == "/api/expect":
            self._handle_expect(payload)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_review(self, payload: dict[str, Any]) -> None:
        message = payload.get("message")
        reviewer = payload.get("reviewer", "regex")
        if not isinstance(message, str) or not message.strip():
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "message is required"})
            return
        if reviewer not in {"regex", "fake", "ollama"}:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "reviewer must be regex, fake, or ollama"},
            )
            return
        try:
            reviewer_config, review_engine = self._reviewer_options(reviewer, payload)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if reviewer != self.workbench.reviewer_type or reviewer_config != self.workbench.reviewer_config:
            self.workbench.close()
            type(self).workbench = ReviewWorkbench.sandbox(
                reviewer_type=reviewer,
                review_engine=review_engine,
                reviewer_config=reviewer_config,
            )
            type(self).runs = {}
        run = self.workbench.review(message)
        self.runs[run.run_id] = run
        self._send_json(HTTPStatus.OK, run.to_dict())

    def _handle_apply(self, payload: dict[str, Any]) -> None:
        run_id = payload.get("run_id")
        if not isinstance(run_id, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})
            return
        run = self.runs.get(run_id)
        if run is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "run not found"})
            return
        applied = self.workbench.apply(run)
        self.runs[run_id] = applied
        self._send_json(HTTPStatus.OK, applied.to_dict())

    def _handle_expect(self, payload: dict[str, Any]) -> None:
        run_id = payload.get("run_id")
        target = payload.get("target")
        contains = payload.get("contains")
        if not isinstance(run_id, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})
            return
        if not isinstance(target, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "target is required"})
            return
        if not isinstance(contains, str) or not contains.strip():
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "contains cannot be empty"})
            return
        run = self.runs.get(run_id)
        if run is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "run not found"})
            return
        try:
            checked = self.workbench.expect(run, target=target, contains=contains)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self.runs[run_id] = checked
        self._send_json(HTTPStatus.OK, checked.to_dict())

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8") if raw else "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("invalid JSON")
        return payload

    def _reviewer_options(
        self,
        reviewer: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], object | None]:
        if reviewer != "ollama":
            return {}, None
        model = _text_option(payload.get("model"), "qwen2.5:7b")
        base_url = _text_option(payload.get("base_url"), "http://127.0.0.1:11434")
        timeout_seconds = _timeout_option(payload.get("timeout"), 30)
        config = {
            "model": model,
            "base_url": base_url,
            "timeout_seconds": timeout_seconds,
        }
        return (
            config,
            OllamaReviewEngine(
                model=model,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            ),
        )

    def _send(self, status: HTTPStatus, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False), "application/json")


def create_workbench_handler(
    workbench: ReviewWorkbench | None = None,
) -> type[WorkbenchRequestHandler]:
    selected_workbench = workbench if workbench is not None else ReviewWorkbench.sandbox()

    class Handler(WorkbenchRequestHandler):
        workbench = selected_workbench
        runs: dict[str, WorkbenchRun] = {}

    return Handler


def serve_workbench(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), create_workbench_handler())
    address, selected_port = server.server_address
    print(f"Review Workbench: http://{address}:{selected_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _text_option(value: Any, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError("Ollama options must be strings")
    cleaned = value.strip()
    return cleaned or default


def _timeout_option(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("timeout must be a number") from exc
    if timeout <= 0:
        raise ValueError("timeout must be greater than 0")
    return timeout
