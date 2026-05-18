import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from minchoagnt.web import create_workbench_handler


class WebServerContext:
    def __enter__(self):
        self.handler = create_workbench_handler()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.handler.workbench.close()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response, data

    def post_json(self, path, payload):
        return self.request(
            "POST",
            path,
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )


class ReviewWorkbenchWebTests(unittest.TestCase):
    def test_root_serves_workbench_html(self):
        with WebServerContext() as server:
            response, data = server.request("GET", "/")

        html = data.decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("Review Workbench", html)
        self.assertIn("~ Review", html)
        self.assertIn("! Apply", html)
        self.assertIn("ollama", html)
        self.assertIn("Ollama Model", html)
        self.assertIn("? Verify", html)
        self.assertIn("Expect Target", html)

    def test_review_and_apply_api_flow(self):
        with WebServerContext() as server:
            review_response, review_data = server.post_json(
                "/api/review",
                {
                    "message": "remember: I prefer Korean summaries.",
                    "reviewer": "regex",
                },
            )
            review_payload = json.loads(review_data)

            apply_response, apply_data = server.post_json(
                "/api/apply",
                {"run_id": review_payload["run_id"]},
            )
            apply_payload = json.loads(apply_data)

        self.assertEqual(review_response.status, 200)
        self.assertEqual(review_payload["run_id"], "run_001")
        self.assertEqual(
            review_payload["review_plan"]["memory_additions"],
            [{"target": "user", "content": "I prefer Korean summaries."}],
        )
        self.assertEqual(apply_response.status, 200)
        self.assertEqual(apply_payload["apply_result"]["memory_saved"], 1)
        self.assertEqual(apply_payload["diff"]["user"]["added"], ["I prefer Korean summaries."])
        self.assertEqual(apply_payload["node_status"]["StateDiff"], "success")

    def test_expect_api_checks_applied_run(self):
        with WebServerContext() as server:
            _, review_data = server.post_json(
                "/api/review",
                {
                    "message": "remember: I prefer Korean summaries.",
                    "reviewer": "regex",
                },
            )
            run_id = json.loads(review_data)["run_id"]
            server.post_json("/api/apply", {"run_id": run_id})

            expect_response, expect_data = server.post_json(
                "/api/expect",
                {
                    "run_id": run_id,
                    "target": "user",
                    "contains": "Korean summaries",
                },
            )
            expect_payload = json.loads(expect_data)

        self.assertEqual(expect_response.status, 200)
        self.assertEqual(
            expect_payload["check_result"],
            {
                "target": "user",
                "contains": "Korean summaries",
                "passed": True,
                "message": "matched user memory",
            },
        )
        self.assertIn(
            {"step": "expect", "status": "success", "message": "? verify passed"},
            expect_payload["events"],
        )

    def test_expect_api_rejects_empty_contains(self):
        with WebServerContext() as server:
            response, data = server.post_json(
                "/api/expect",
                {
                    "run_id": "run_404",
                    "target": "user",
                    "contains": "",
                },
            )

        payload = json.loads(data)
        self.assertEqual(response.status, 400)
        self.assertEqual(payload["error"], "contains cannot be empty")

    def test_review_api_rejects_malformed_json(self):
        with WebServerContext() as server:
            response, data = server.request(
                "POST",
                "/api/review",
                body="{bad json",
                headers={"Content-Type": "application/json"},
            )

        payload = json.loads(data)
        self.assertEqual(response.status, 400)
        self.assertEqual(payload["error"], "invalid JSON")

    def test_review_api_can_select_ollama_reviewer_with_config(self):
        created = []

        class FakeOllamaReviewEngine:
            def __init__(self, model, base_url, timeout_seconds):
                self.model = model
                self.base_url = base_url
                self.timeout_seconds = timeout_seconds
                created.append((model, base_url, timeout_seconds))

            def review(self, messages, review_memory=True, review_skills=True):
                from minchoagnt.review import MemoryAddition, ReviewPlan

                return ReviewPlan(
                    memory_additions=[
                        MemoryAddition(target="user", content="I prefer Korean summaries.")
                    ],
                    skill_creations=[],
                )

        with patch("minchoagnt.web.OllamaReviewEngine", FakeOllamaReviewEngine):
            with WebServerContext() as server:
                response, data = server.post_json(
                    "/api/review",
                    {
                        "message": "remember: I prefer Korean summaries.",
                        "reviewer": "ollama",
                        "model": "qwen2.5:7b",
                        "base_url": "http://127.0.0.1:11434",
                        "timeout": 2.5,
                    },
                )

        payload = json.loads(data)
        self.assertEqual(response.status, 200)
        self.assertEqual(created, [("qwen2.5:7b", "http://127.0.0.1:11434", 2.5)])
        self.assertEqual(
            payload["reviewer"],
            {
                "type": "ollama",
                "model": "qwen2.5:7b",
                "base_url": "http://127.0.0.1:11434",
                "timeout_seconds": 2.5,
            },
        )
        self.assertEqual(payload["node_status"]["ReviewPlan"], "success")

    def test_review_api_rejects_invalid_ollama_timeout(self):
        with WebServerContext() as server:
            response, data = server.post_json(
                "/api/review",
                {
                    "message": "remember: I prefer Korean summaries.",
                    "reviewer": "ollama",
                    "timeout": 0,
                },
            )

        payload = json.loads(data)
        self.assertEqual(response.status, 400)
        self.assertEqual(payload["error"], "timeout must be greater than 0")


if __name__ == "__main__":
    unittest.main()
