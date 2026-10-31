# Project rules for AI assistants

## Architecture
- Layers: `routes` -> `nodes` -> `providers`. Nodes never import SDKs; only `providers/` does.
- All data contracts live in `app/schemas.py`. Do not change them without asking.
- Eligibility (`nodes/evaluate.py`) is pure Python. Never call an LLM there.

## Hard rules
- NEVER add hardcoded, mock, sample, or placeholder data to `app/`. Test fixtures go in `tests/` only.
- Every extracted fact must include `clause_id` and an exact quote.
- All LLM outputs must be validated against a Pydantic schema, with retry on failure.
- Prompts go in `app/prompts/*.md`, never inline in Python.
- Config and secrets come from environment via `app/config.py`.

## Style
- Type hints on every function. Async for I/O.
- One responsibility per module; keep functions small.
- Add or update a unit test for every new pure function.
- Raise typed errors (`UnreadableDocument`, `ProviderError`, `NotAPolicy`); no bare `except`.

