import json
import unittest

from minchoagnt.ollama import OllamaReviewEngine
from minchoagnt.sessions import Message


class FakeOllamaClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post_json(self, url, payload, timeout_seconds):
        self.calls.append((url, payload, timeout_seconds))
        if self.error:
            raise self.error
        return self.response


def user_message(content):
    return Message(
        id=1,
        session_id="session-1",
        role="user",
        content=content,
        timestamp=1.0,
    )


class OllamaReviewEngineTests(unittest.TestCase):
    def test_calls_ollama_chat_and_parses_review_plan_json(self):
        raw_plan = {
            "memory_additions": [
                {
                    "target": "user",
                    "content": "사용자는 한국어 요약을 선호한다.",
                    "evidence": "기억해줘: 나는 한국어 요약을 선호해",
                }
            ],
            "skill_creations": [],
        }
        client = FakeOllamaClient(
            response={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(raw_plan, ensure_ascii=False),
                }
            }
        )
        engine = OllamaReviewEngine(
            model="qwen2.5:7b",
            base_url="http://127.0.0.1:11434",
            client=client,
            timeout_seconds=7,
        )

        plan = engine.review([user_message("기억해줘: 나는 한국어 요약을 선호해")])

        self.assertEqual(plan.memory_additions[0].content, "사용자는 한국어 요약을 선호한다.")
        self.assertEqual(plan.memory_additions[0].evidence, "기억해줘: 나는 한국어 요약을 선호해")
        self.assertIsNone(engine.last_error)

        url, payload, timeout = client.calls[0]
        self.assertEqual(url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(timeout, 7)
        self.assertEqual(payload["model"], "qwen2.5:7b")
        self.assertEqual(payload["stream"], False)
        self.assertEqual(payload["format"], "json")
        self.assertEqual(payload["options"]["temperature"], 0)
        self.assertIn("Return only JSON", payload["messages"][0]["content"])
        self.assertIn("기억해줘", payload["messages"][1]["content"])

    def test_filters_output_by_requested_review_flags(self):
        raw_plan = {
            "memory_additions": [
                {"target": "user", "content": "사용자는 한국어 요약을 선호한다."}
            ],
            "skill_creations": [
                {
                    "name": "release-checklist",
                    "content": "# Release Checklist\n\n1. Run tests.",
                    "category": "learned",
                }
            ],
        }
        client = FakeOllamaClient(
            response={"message": {"content": json.dumps(raw_plan, ensure_ascii=False)}}
        )
        engine = OllamaReviewEngine(model="qwen2.5:7b", client=client)

        plan = engine.review(
            [user_message("릴리즈 절차를 스킬로 저장해줘")],
            review_memory=False,
            review_skills=True,
        )

        self.assertEqual(plan.memory_additions, [])
        self.assertEqual(len(plan.skill_creations), 1)
        self.assertIn("review_memory=false", client.calls[0][1]["messages"][1]["content"])
        self.assertIn("review_skills=true", client.calls[0][1]["messages"][1]["content"])

    def test_returns_empty_plan_when_client_fails(self):
        client = FakeOllamaClient(error=TimeoutError("ollama timed out"))
        engine = OllamaReviewEngine(model="qwen2.5:7b", client=client)

        plan = engine.review([user_message("anything")])

        self.assertEqual(plan.memory_additions, [])
        self.assertEqual(plan.skill_creations, [])
        self.assertIn("ollama timed out", engine.last_error)

    def test_does_not_swallow_unexpected_programming_errors(self):
        client = FakeOllamaClient(error=RuntimeError("programmer mistake"))
        engine = OllamaReviewEngine(model="qwen2.5:7b", client=client)

        with self.assertRaisesRegex(RuntimeError, "programmer mistake"):
            engine.review([user_message("anything")])

    def test_returns_empty_plan_when_model_returns_invalid_schema(self):
        client = FakeOllamaClient(
            response={
                "message": {
                    "content": json.dumps(
                        {
                            "memory_additions": [
                                {"target": "profile", "content": "bad target"}
                            ],
                            "skill_creations": [],
                        }
                    )
                }
            }
        )
        engine = OllamaReviewEngine(model="qwen2.5:7b", client=client)

        plan = engine.review([user_message("anything")])

        self.assertEqual(plan.memory_additions, [])
        self.assertEqual(plan.skill_creations, [])
        self.assertIn("target", engine.last_error)


if __name__ == "__main__":
    unittest.main()
