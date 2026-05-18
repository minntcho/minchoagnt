# minchoagnt

A tiny, local-only slice of a Hermes-style agent loop.

This project demonstrates the mechanics behind an agent that can:

- persist bounded declarative memory across sessions
- save reusable procedural skills as `SKILL.md` files
- log conversations to SQLite
- run a small review loop that promotes conversation facts into memory or skills

The default review loop is heuristic so the core storage and orchestration pieces
stay easy to inspect and test. An Ollama-backed reviewer is available when you
want to experiment with a local LLM.

## Try It

```powershell
python -m minchoagnt say "remember: I prefer Korean summaries." --memory-interval 1
python -m minchoagnt say "remember: I prefer Korean summaries." --memory-interval 1 --reviewer ollama --model qwen2.5:7b
python -m minchoagnt context
python -m minchoagnt say "skill: release-checklist | run tests; inspect git status; push branch" --skill-interval 1 --tool-iterations 1
python -m minchoagnt skills list
python -m minchoagnt skills view release-checklist
python -m minchoagnt search Korean
python -m minchoagnt workbench --host 127.0.0.1 --port 8000
```

By default, local state is written to `.minchoagnt/` in the current directory. Set
`MINCHOAGNT_HOME` or pass `--home` to use a different state directory.

## Use Ollama As A Reviewer

Start Ollama locally, pull a model, then select the Ollama reviewer from the CLI.

```powershell
python -m minchoagnt say "remember: I prefer Korean summaries." --memory-interval 1 --reviewer ollama --model qwen2.5:7b
```

You can also inject `OllamaReviewEngine` directly when constructing an agent.

```python
from minchoagnt import MiniAgent, OllamaReviewEngine

agent = MiniAgent(
    ".minchoagnt",
    memory_interval=1,
    review_engine=OllamaReviewEngine(model="qwen2.5:7b"),
)

agent.chat("기억해줘: 나는 한국어 요약을 선호해")
```

If Ollama is unavailable or the model returns invalid JSON, the reviewer returns
an empty plan and records the failure in `OllamaReviewEngine.last_error`.

## Test

```powershell
python -m unittest discover -s tests -v
```

## Design Docs

- [Review Workbench MVP](docs/superpowers/specs/2026-05-18-review-workbench-mvp-design.md)
