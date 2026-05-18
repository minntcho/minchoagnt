# minchoagnt

A tiny, local-only slice of a Hermes-style agent loop.

This project demonstrates the mechanics behind an agent that can:

- persist bounded declarative memory across sessions
- save reusable procedural skills as `SKILL.md` files
- log conversations to SQLite
- run a small review loop that promotes conversation facts into memory or skills

It intentionally does not call an LLM yet. The review loop is heuristic so the core
storage and orchestration pieces stay easy to inspect and test.

## Try It

```powershell
python -m minchoagnt say "remember: I prefer Korean summaries." --memory-interval 1
python -m minchoagnt context
python -m minchoagnt say "skill: release-checklist | run tests; inspect git status; push branch" --skill-interval 1 --tool-iterations 1
python -m minchoagnt skills list
python -m minchoagnt skills view release-checklist
python -m minchoagnt search Korean
```

By default, local state is written to `.minchoagnt/` in the current directory. Set
`MINCHOAGNT_HOME` or pass `--home` to use a different state directory.

## Test

```powershell
python -m unittest discover -s tests -v
```
