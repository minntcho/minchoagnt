from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol, Sequence

from minchoagnt.review import ReviewPlan
from minchoagnt.sessions import Message


class OllamaClientProtocol(Protocol):
    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        """POST JSON to an Ollama-compatible endpoint and return decoded JSON."""


class OllamaHTTPClient:
    """Small stdlib HTTP client for Ollama's `/api/chat` endpoint."""

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
        decoded = json.loads(body)
        if not isinstance(decoded, dict):
            raise ValueError("Ollama response JSON must be an object.")
        return decoded


class OllamaReviewEngine:
    """ReviewEngine implementation backed by an Ollama local chat model."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        client: OllamaClientProtocol | None = None,
        timeout_seconds: float = 30,
        temperature: float = 0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = client if client is not None else OllamaHTTPClient()
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.last_error: str | None = None

    def review(
        self,
        messages: Sequence[Message],
        review_memory: bool = True,
        review_skills: bool = True,
    ) -> ReviewPlan:
        self.last_error = None
        try:
            response = self.client.post_json(
                f"{self.base_url}/api/chat",
                self._payload(messages, review_memory, review_skills),
                self.timeout_seconds,
            )
            plan = ReviewPlan.from_json(self._content_from_response(response))
            return self._filter_plan(plan, review_memory, review_skills)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            self.last_error = str(exc)
            return ReviewPlan()

    def _payload(
        self,
        messages: Sequence[Message],
        review_memory: bool,
        review_skills: bool,
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": self._review_prompt(messages, review_memory, review_skills),
                },
            ],
        }

    @staticmethod
    def _content_from_response(response: dict[str, Any]) -> str:
        message = response.get("message")
        if not isinstance(message, dict):
            raise ValueError("Ollama response is missing message object.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama response message.content must be a non-empty string.")
        return content

    @staticmethod
    def _filter_plan(
        plan: ReviewPlan,
        review_memory: bool,
        review_skills: bool,
    ) -> ReviewPlan:
        return ReviewPlan(
            memory_additions=plan.memory_additions if review_memory else [],
            skill_creations=plan.skill_creations if review_skills else [],
        )

    @staticmethod
    def _system_prompt() -> str:
        return """You are a background review engine for a local agent.
Return only JSON. Do not wrap the JSON in markdown.

The JSON must match this shape:
{
  "memory_additions": [
    {
      "target": "user" or "memory",
      "content": "durable fact to remember",
      "evidence": "short exact evidence from the conversation"
    }
  ],
  "skill_creations": [
    {
      "name": "safe skill name",
      "content": "complete SKILL.md markdown",
      "category": "learned",
      "evidence": "short exact evidence from the conversation"
    }
  ]
}

Use target "user" for stable user preferences or profile facts.
Use target "memory" for stable project, environment, or workflow facts.
Only include items that are durable enough to be useful in future sessions."""

    @staticmethod
    def _review_prompt(
        messages: Sequence[Message],
        review_memory: bool,
        review_skills: bool,
    ) -> str:
        flags = (
            f"review_memory={str(review_memory).lower()}\n"
            f"review_skills={str(review_skills).lower()}"
        )
        conversation = "\n".join(
            f"{message.role}: {message.content}" for message in messages
        )
        return f"""{flags}

If review_memory=false, return an empty memory_additions list.
If review_skills=false, return an empty skill_creations list.

Conversation:
{conversation}"""
