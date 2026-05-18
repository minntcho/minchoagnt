import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from minchoagnt import cli
from minchoagnt.agent import ChatResult, ReviewSummary


class FakeAgent:
    instances = []

    def __init__(self, home, memory_interval=10, skill_interval=10, review_engine=None):
        self.home = home
        self.memory_interval = memory_interval
        self.skill_interval = skill_interval
        self.review_engine = review_engine
        self.chat_calls = []
        self.__class__.instances.append(self)

    def chat(self, text, tool_iterations=0):
        self.chat_calls.append((text, tool_iterations))
        return ChatResult(
            session_id="session-1",
            response="recorded",
            review=ReviewSummary(memory_saved=0, skills_created=0),
        )


class FakeOllamaReviewEngine:
    def __init__(self, model, base_url, timeout_seconds):
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds


class FakeWorkbenchServer:
    calls = []

    @classmethod
    def serve(cls, host, port):
        cls.calls.append((host, port))


class CLITests(unittest.TestCase):
    def setUp(self):
        FakeAgent.instances = []
        FakeWorkbenchServer.calls = []

    def test_say_defaults_to_regex_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cli, "MiniAgent", FakeAgent):
                with redirect_stdout(io.StringIO()):
                    exit_code = cli.main(["--home", tmp, "say", "hello"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(FakeAgent.instances[0].home, Path(tmp))
        self.assertIsNone(FakeAgent.instances[0].review_engine)
        self.assertEqual(FakeAgent.instances[0].chat_calls, [("hello", 0)])

    def test_say_can_inject_ollama_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cli, "MiniAgent", FakeAgent):
                with patch.object(cli, "OllamaReviewEngine", FakeOllamaReviewEngine):
                    with redirect_stdout(io.StringIO()):
                        exit_code = cli.main(
                            [
                                "--home",
                                tmp,
                                "say",
                                "기억해줘: 나는 한국어 요약을 선호해",
                                "--reviewer",
                                "ollama",
                                "--model",
                                "qwen2.5:7b",
                                "--ollama-url",
                                "http://127.0.0.1:11434",
                                "--timeout",
                                "2.5",
                                "--memory-interval",
                                "1",
                            ]
                        )

        self.assertEqual(exit_code, 0)
        engine = FakeAgent.instances[0].review_engine
        self.assertIsInstance(engine, FakeOllamaReviewEngine)
        self.assertEqual(engine.model, "qwen2.5:7b")
        self.assertEqual(engine.base_url, "http://127.0.0.1:11434")
        self.assertEqual(engine.timeout_seconds, 2.5)
        self.assertEqual(FakeAgent.instances[0].memory_interval, 1)

    def test_workbench_command_starts_local_server(self):
        with patch.object(cli, "serve_workbench", FakeWorkbenchServer.serve):
            with redirect_stdout(io.StringIO()):
                exit_code = cli.main(
                    [
                        "workbench",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "9001",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(FakeWorkbenchServer.calls, [("127.0.0.1", 9001)])


if __name__ == "__main__":
    unittest.main()
