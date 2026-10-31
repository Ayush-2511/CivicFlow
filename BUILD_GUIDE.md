# Build Guide: Scheme Explainer Architecture

How to build the architecture phase by phase. Each phase has a goal, the files you touch, the steps, and a **done-when** check. Do not start a phase until the previous one's check passes.

> Code snippets are skeletons to show shape and intent. Library APIs (especially LangGraph and the LLM SDK) change between versions, so check the current docs for exact function names before pasting.

---

## 0. Ground rules (read once, enforce always)

1. **LLM extracts and explains. Plain code decides eligibility.**
2. **Only `providers/` imports SDKs.** Nodes call provider interfaces.
3. **Every extracted fact carries `clause_id` + `quote`.** No source, no fact.
4. **No hardcoded or mock data anywhere in `app/`.** Test fixtures live in `tests/` only.
5. **All LLM outputs are validated against Pydantic schemas**, with retry on failure.
6. **Prompts live in `app/prompts/*.md`**, not inside Python strings.
7. **Everyone on the team must be able to explain every node.** Review every AI-generated diff.

---

## Phase 1: Skeleton and contracts

**Goal:** a running FastAPI app, config, and all data contracts defined. No AI yet.

**Files:** `pyproject.toml`, `.env.example`, `app/main.py`, `app/config.py`, `app/schemas.py`, `AGENTS.md`

### Steps
1. Create the repo and a Python virtual environment. Dependencies to start with: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `httpx`, `langgraph`, `pypdf` (or `pymupdf`), `rank-bm25`, `pytest`, plus your LLM SDK.
2. Write `config.py` with `pydantic-settings`: API keys, model names (fast and strong), timeouts, supported languages. All read from `.env`.
3. Write `schemas.py` **yourself** before touching anything else. This is the most important file in the project.
4. Write `AGENTS.md` (template in section A below) so Antigravity follows the rules.
5. `main.py`: app with a `/health` route.

### `schemas.py` skeleton
```python
from enum import Enum
from pydantic import BaseModel, Field

class Operator(str, Enum):
    LT = "lt"; LTE = "lte"; GT = "gt"; GTE = "gte"
    EQ = "eq"; NEQ = "neq"; IN = "in"; NOT_IN = "not_in"

class Field_(str, Enum):           # controlled vocabulary: interview + engine share it
    AGE = "age"
    ANNUAL_INCOME = "annual_income"
    LAND_HECTARES = "land_hectares"
    STATE = "state"
    CATEGORY = "category"
    BUSINESS_TYPE = "business_type"
    ANNUAL_TURNOVER = "annual_turnover"
    EMPLOYEES = "employees"
    # extend as real documents demand it

class Clause(BaseModel):
    id: str                         # stable, e.g. "doc1-p3-c12"
    doc_id: str
    page: int
    text: str

class Cited(BaseModel):
    clause_id: str
    quote: str                      # exact substring of the clause text

class Condition(Cited):
    field: Field_
    operator: Operator
    value: float | str | list[str]
    unit: str | None = None

class Benefit(Cited):
    description: str
    amount: float | None = None
    frequency: str | None = None    # "yearly", "monthly", "one-time"

class Obligation(Cited):
    description: str
    deadline: str | None = None
    required_documents: list[str] = []
    apply_at: str | None = None

class Scheme(BaseModel):
    doc_id: str
    title: str
    audience: str                   # "citizen" | "business"
    benefits: list[Benefit] = []
    conditions: list[Condition] = []
    obligations: list[Obligation] = []
    uncertain: list[str] = []       # things the verifier could not confirm

class Reason(BaseModel):
    condition: Condition
    passed: bool | None             # None = could not evaluate (missing field)

class Verdict(BaseModel):
    status: str                     # "YES" | "NO" | "MAYBE"
    reasons: list[Reason]
    missing_fields: list[Field_] = []

class Segment(BaseModel):
    text: str                       # already in target language
    clause_ids: list[str]

class Explainer(BaseModel):
    language: str
    segments: list[Segment]
    checklist: list[str]
    audio_urls: list[str] = []
```

**Done when:** `uvicorn app.main:app` runs, `/health` returns OK, and `schemas.py` imports cleanly. Show the schemas to the whole team and agree on them. Changing them later is expensive.

---

## Phase 2: Providers (the only SDK-touching code)

**Goal:** LLM and speech behind small interfaces you can swap or fake in tests.

**Files:** `app/providers/llm.py`, `app/providers/speech.py`

### Steps
1. Define an `LLM` protocol with two methods:
   - `generate_structured(prompt, schema, *, tier, images=None) -> BaseModel`
   - `generate_text(prompt, *, tier) -> str`
   `tier` is `"fast"` or `"strong"` and maps to model names from config.
2. Implement it once for your chosen model. Inside `generate_structured`: request JSON matching the schema, validate with Pydantic, retry up to N times on validation failure (pass the validation error back to the model), apply a timeout, back off on rate limits, and raise a typed `ProviderError` on final failure.
3. Define `TTS` protocol: `synthesize(text, language) -> bytes`. Implement one provider, then add a fallback provider if time allows.
4. **Test Indian-language TTS quality now**, with legal vocabulary, before committing to a provider.

### Skeleton
```python
from typing import Protocol, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLM(Protocol):
    async def generate_structured(self, prompt: str, schema: Type[T], *,
                                  tier: str = "strong", images: list[bytes] | None = None) -> T: ...
    async def generate_text(self, prompt: str, *, tier: str = "fast") -> str: ...

class TTS(Protocol):
    async def synthesize(self, text: str, language: str) -> bytes: ...
```

**Done when:** a script can call `generate_structured` with a tiny schema and get a validated object, and `synthesize` returns playable audio in Hindi (and your second language).

---

## Phase 3: Ingest, parse, index

**Goal:** turn a real document into a list of `Clause` objects with stable IDs.

**Files:** `nodes/ingest.py`, `nodes/parse.py`, `nodes/index.py`, `providers/sources.py`, `store.py`

### Steps
1. **Ingest:** accept an uploaded file (PDF/image) or a URL. Compute a SHA-256 hash of the bytes as `doc_id`. Check the SQLite cache by hash.
2. **Parse (smart order):**
   - Try the PDF text layer first (fast, free).
   - If the text is empty or very short, send page images to the vision model for OCR.
   - Images (from a phone camera) always go to the vision model.
   - Return text with page numbers. If the quality is bad (too little text, garbled), raise a typed `UnreadableDocument` error so the UI can ask for a retake.
3. **Clause splitting:** split by numbered sections or paragraphs ("1.", "(a)", "Section 4"), falling back to paragraph chunks of a sensible size. Assign IDs like `{doc_id[:6]}-p{page}-c{n}`.
4. **Index:** build an in-memory BM25 index over clauses (add embeddings only if retrieval quality demands it). Documents are small, so no vector DB needed.
5. `sources.py`: fetchers for official sources (e-Gazette, PIB, myScheme, data.gov.in). Build **one** that works reliably and live. This is your "real-time backend" proof for the no-dummy-data rule.

**Done when:** feeding 3 different real documents (one text PDF, one scan, one phone photo) yields sensible clause lists, and a garbage file produces a clean typed error.

---

## Phase 4: Extract and verify (spend your best hours here)

**Goal:** a `Scheme` object where every item is provably backed by the source.

**Files:** `nodes/extract.py`, `nodes/verify.py`, `prompts/extract.md`, `prompts/verify.md`

### Extraction steps
1. Group clauses into sections (by size). Run extraction over sections **concurrently** with `asyncio.gather`.
2. The prompt must instruct: output only what the text explicitly states; for each item give `clause_id` and an **exact quote**; use only fields from the controlled vocabulary; if a rule doesn't map to a known field, put it in `uncertain` instead of inventing a field.
3. Merge section results, dedupe conditions.

### Verification steps (cheap first)
1. **String check:** is `quote` actually a substring of the clause text (after whitespace/case normalization, with fuzzy tolerance)? This catches most hallucinations at zero cost.
2. **Value check:** does the number in `value` appear in the quote? ("1.5 lakh" vs `150000`: normalize Indian number formats.)
3. **LLM re-check (only for failures):** fast model gets quote + extracted item and answers "does this text support this exact claim?" in structured form.
4. **Loop:** failed items go back to extraction with the failure reason, up to 2 retries. Still failing → move to `uncertain` and lower confidence. Never present an unverified item as fact.

### Skeleton
```python
def check_quote(item: Cited, clauses: dict[str, Clause]) -> bool:
    clause = clauses.get(item.clause_id)
    if not clause:
        return False
    return normalize(item.quote) in normalize(clause.text)   # + fuzzy fallback
```

**Done when:** on 3 real documents you can print every condition with its clause and quote, a deliberately corrupted extraction (planted in a test) gets caught, and ambiguous clauses land in `uncertain`.

---

## Phase 5: Interview and evaluate

**Goal:** ask only the questions that matter, then compute a verdict deterministically.

**Files:** `nodes/interview.py`, `nodes/evaluate.py`

### Steps
1. **Interview node:** from `scheme.conditions`, collect the distinct `Field_` values. Skip fields already in the user's profile. Output the list of questions (one per field) with a plain-language label per field (a static label map keyed by `Field_` is fine; this is UI text, not data).
2. In LangGraph this is an **interrupt**: the graph pauses, the UI collects answers, and `POST /session/{id}/answers` resumes it. Persist state with a SQLite checkpointer.
3. **Validate answers** (type, range). Invalid → ask again with a friendly message. Skipped → field stays missing.
4. **Evaluate node, pure Python, no LLM:**

```python
OPS = {
    "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b, "gte": lambda a, b: a >= b,
    "eq": lambda a, b: a == b, "neq": lambda a, b: a != b,
    "in": lambda a, b: a in b, "not_in": lambda a, b: a not in b,
}

def evaluate(conditions, profile) -> Verdict:
    reasons, missing = [], []
    for c in conditions:
        if c.field not in profile:
            missing.append(c.field)
            reasons.append(Reason(condition=c, passed=None))
            continue
        reasons.append(Reason(condition=c, passed=OPS[c.operator](profile[c.field], c.value)))
    if any(r.passed is False for r in reasons):
        status = "NO"
    elif missing:
        status = "MAYBE"
    else:
        status = "YES"
    return Verdict(status=status, reasons=reasons, missing_fields=missing)
```

5. Handle unit normalization before comparing (lakh/crore, acres vs hectares). Write this as a small tested helper.
6. If the scheme has `uncertain` items, a YES becomes "YES, subject to checking X in the original".

**Done when:** unit tests cover every operator, boundary values (exactly equal to the limit), missing fields, and unit conversion. This is the easiest module to test thoroughly, so do it.

---

## Phase 6: Compose, localize, voice

**Goal:** a short, plain, clause-tagged explainer in the target language, spoken.

**Files:** `nodes/compose.py`, `nodes/localize.py`, `nodes/voice.py`, `prompts/compose.md`

### Steps
1. **Compose + localize in one call:** input is the verified `Scheme`, the `Verdict`, the persona (citizen or business), and the target language. Output is a list of `Segment`s (already in the target language) with their `clause_ids` preserved, plus the action checklist. The persona decides the order: benefit-first for citizens, obligation-and-deadline-first for businesses.
2. **Constraints in the prompt:** short sentences, everyday words, keep numbers and dates exact, explain legal terms inline, and never add facts that aren't in the input.
3. **Voice:** run TTS **per segment in parallel**, store the audio, and return URLs. For WhatsApp later, convert to OGG/Opus with ffmpeg.
4. Keep segments short (1 to 3 sentences) so audio starts quickly and citations stay granular.

**Done when:** one real document produces a Hindi explainer whose every segment maps to a real clause, and a native speaker (a friend or teammate) confirms it sounds natural and the numbers are right.

---

## Phase 7: Graph wiring and API

**Goal:** all nodes connected, resumable, streaming progress.

**Files:** `app/graph.py`, `routes/pipeline.py`, `routes/session.py`

### Steps
1. Define the graph state (a typed dict or Pydantic model): `doc_id`, `clauses`, `scheme`, `profile`, `verdict`, `explainer`, `errors`, `trace`.
2. Add nodes in order. Add **conditional edges**:
   - after `parse`: unreadable → end with a "please retake" result
   - after `verify`: failures with retries left → back to `extract`
   - after `interview`: needs answers → interrupt
3. Each node appends `{node, status, ms, retries}` to `trace`.
4. `POST /pipeline/start`: accepts the file/URL and persona/language, starts the run, returns a `run_id`.
5. `GET /pipeline/{run_id}/events`: **SSE stream** emitting a progress event as each node completes (powers the UI trace panel).
6. `POST /session/{run_id}/answers`: resumes the paused graph.
7. Typed errors (`UnreadableDocument`, `ProviderError`, `NotAPolicy`) map to clear JSON responses.

### Skeleton
```python
from langgraph.graph import StateGraph, END

g = StateGraph(PipelineState)
g.add_node("ingest", ingest); g.add_node("parse", parse)
g.add_node("index", index);   g.add_node("extract", extract)
g.add_node("verify", verify); g.add_node("interview", interview)
g.add_node("evaluate", evaluate_node); g.add_node("compose", compose)
g.add_node("voice", voice)

g.set_entry_point("ingest")
g.add_edge("ingest", "parse")
g.add_conditional_edges("parse", route_after_parse, {"ok": "index", "bad": END})
g.add_edge("index", "extract"); g.add_edge("extract", "verify")
g.add_conditional_edges("verify", route_after_verify, {"retry": "extract", "ok": "interview"})
g.add_edge("interview", "evaluate"); g.add_edge("evaluate", "compose")
g.add_edge("compose", "voice");      g.add_edge("voice", END)
# compile with a SQLite checkpointer so the interview interrupt can resume
```

**Done when:** one curl/Postman flow runs the whole pipeline: start → watch SSE events → answer questions → receive an explainer with audio.

---

## Phase 8: Frontend (keep it thin)

**Goal:** a demo-ready UI that makes the backend's depth visible.

**Folder:** `frontend/` (Vite + React)

### Screens/components
1. **Upload/URL input** + persona toggle + language picker
2. **Live progress panel** (SSE): each node ticking as it completes, with retries visible
3. **Extracted rules view:** each condition with its clause and a "view original" highlight
4. **Interview form:** only the questions the document needs
5. **Verdict card:** YES/NO/MAYBE, the reasons, the deciding clause highlighted in the source text
6. **Explainer:** audio player per segment, text alongside, tap a segment to see its clause
7. **Action checklist**
8. **Friendly error states** for every typed error

**Done when:** a non-teammate can use it start to finish without instructions.

---

## Phase 9: Robustness pass (30 points live)

Work through this list on purpose, with real bad inputs:

- [ ] Blurry/rotated photo → retake prompt
- [ ] Non-policy document → "this doesn't look like a scheme or policy"
- [ ] Scanned PDF with no text layer → OCR path works
- [ ] Contradictory or ambiguous clauses → MAYBE with reason
- [ ] Invalid, out-of-range, or skipped interview answers
- [ ] Very long document → latency acceptable, progress visible
- [ ] Unsupported language → clear message
- [ ] LLM/TTS timeout or rate limit → retry, fallback, friendly error
- [ ] Network drop mid-run → resumable or clear status
- [ ] Two runs at once don't corrupt each other's state

Also: run the whole thing on the venue's network (or a phone hotspot) before the demo, and pre-check API quotas so you don't hit limits on stage.

---

## Phase 10: Stretch (only if everything above is solid)

1. **Live source fetching:** a "fetch latest from official site" button using `providers/sources.py`.
2. **Change detection:** diff two versions of a notification and say what changed for this user.
3. **WhatsApp channel:** `routes/whatsapp.py` receives the image, calls the same graph, replies with an OGG/Opus voice note. Interview answers by buttons or text first; voice-in (STT) last.

---

## Section A: `AGENTS.md` template (for Antigravity)

```markdown
# Project rules for AI assistants

## Architecture
- Layers: routes -> nodes -> providers. Nodes never import SDKs; only providers/ does.
- All data contracts live in app/schemas.py. Do not change them without asking.
- Eligibility (nodes/evaluate.py) is pure Python. Never call an LLM there.

## Hard rules
- NEVER add hardcoded, mock, sample, or placeholder data to app/. Test fixtures go in tests/ only.
- Every extracted fact must include clause_id and an exact quote.
- All LLM outputs must be validated against a Pydantic schema, with retry on failure.
- Prompts go in app/prompts/*.md, never inline in Python.
- Config and secrets come from environment via app/config.py.

## Style
- Type hints on every function. Async for I/O.
- One responsibility per module; keep functions small.
- Add or update a unit test for every new pure function.
- Raise typed errors (UnreadableDocument, ProviderError, NotAPolicy); no bare except.
```

---

## Section B: Antigravity prompts per phase (examples)

- **Phase 2:** "Implement `providers/llm.py` against the `LLM` protocol using <SDK>. `generate_structured` must validate against the given Pydantic schema, retry up to 3 times feeding the validation error back, apply a timeout, and raise `ProviderError` on failure. Add tests using a fake client."
- **Phase 4:** "Implement `nodes/verify.py` per Phase 4 of BUILD_GUIDE.md: normalized substring check, Indian number-format value check, LLM re-check only for failures, and a bounded retry loop. Include a test where a planted wrong quote is caught."
- **Phase 5:** "Implement `nodes/evaluate.py` as pure Python per the skeleton. Add unit tests for every operator, boundary values, missing fields, and lakh/crore/acre conversion."

Keep each prompt scoped to one module, then **read the diff** and make sure you can explain it before moving on.

---

## Suggested team split

| Role | Owns |
|---|---|
| A | Providers, parse/ingest, sources (Phases 2 and 3) |
| B | Extract + verify + prompts (Phase 4), the highest-leverage area |
| C | Interview, evaluate, tests (Phase 5), then graph wiring (Phase 7) |
| D | Compose/localize/voice (Phase 6), then frontend (Phase 8) |

Solo or a small team? Do phases in order and cut Phase 10 entirely. Whoever writes a module walks the others through it at the end of each phase, so everyone can answer judges' questions.
