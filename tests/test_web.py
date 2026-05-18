import http.client
import json
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


if __name__ == "__main__":
    unittest.main()
