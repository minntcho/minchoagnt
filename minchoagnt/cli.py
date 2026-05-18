from __future__ import annotations

import argparse
import os
from pathlib import Path

from minchoagnt.agent import MiniAgent
from minchoagnt.memory import MemoryStore
from minchoagnt.ollama import OllamaReviewEngine
from minchoagnt.sessions import SessionDB
from minchoagnt.skills import SkillStore


def default_home() -> Path:
    configured = os.environ.get("MINCHOAGNT_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / ".minchoagnt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tiny Hermes-style agent slice.")
    parser.add_argument("--home", type=Path, default=default_home(), help="State directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    say = sub.add_parser("say", help="Record a user turn and maybe run review.")
    say.add_argument("text")
    say.add_argument("--tool-iterations", type=int, default=0)
    say.add_argument("--memory-interval", type=int, default=10)
    say.add_argument("--skill-interval", type=int, default=10)
    say.add_argument("--reviewer", choices=["regex", "ollama"], default="regex")
    say.add_argument("--model", default="qwen2.5:7b", help="Ollama model for --reviewer ollama.")
    say.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL for --reviewer ollama.",
    )
    say.add_argument(
        "--timeout",
        type=float,
        default=30,
        help="Ollama request timeout in seconds for --reviewer ollama.",
    )

    sub.add_parser("context", help="Print the assembled prompt context.")

    memory = sub.add_parser("memory", help="Inspect memory.")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    memory_list = memory_sub.add_parser("list")
    memory_list.add_argument("--target", choices=["memory", "user"], default="memory")

    skills = sub.add_parser("skills", help="Inspect skills.")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    skills_sub.add_parser("list")
    skill_view = skills_sub.add_parser("view")
    skill_view.add_argument("name")

    search = sub.add_parser("search", help="Search session messages.")
    search.add_argument("query")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    home = args.home.expanduser()

    if args.command == "say":
        agent = MiniAgent(
            home,
            memory_interval=args.memory_interval,
            skill_interval=args.skill_interval,
            review_engine=review_engine_from_args(args),
        )
        result = agent.chat(args.text, tool_iterations=args.tool_iterations)
        print(result.response)
        if result.review.memory_saved or result.review.skills_created:
            print(
                "review: "
                f"memory_saved={result.review.memory_saved}, "
                f"skills_created={result.review.skills_created}"
            )
        return 0

    if args.command == "context":
        print(MiniAgent(home).context())
        return 0

    if args.command == "memory":
        store = MemoryStore(home).load()
        for entry in store.entries(args.target):
            print(f"- {entry}")
        return 0

    if args.command == "skills":
        store = SkillStore(home)
        if args.skills_command == "list":
            for name in store.list_names():
                print(name)
            return 0
        print(store.view(args.name), end="")
        return 0

    if args.command == "search":
        db = SessionDB(home / "state.db")
        for message in db.search_messages(args.query):
            print(f"{message.session_id} {message.role}: {message.content}")
        return 0

    return 1


def review_engine_from_args(args):
    if args.reviewer == "ollama":
        return OllamaReviewEngine(
            model=args.model,
            base_url=args.ollama_url,
            timeout_seconds=args.timeout,
        )
    return None
