# Multilingual Policy, Rights & Scheme Explainer: Project Brief

> Problem statement: an intelligent system that ingests government notifications, welfare policy drafts, or municipal laws and converts them into plain, regional-language voice explainers highlighting exact rights, eligibility, and real-world impacts for citizens and small businesses.

---

## 1. What the PS actually asks for

Government text is written for lawyers. The system takes it and produces something a farmer or a small shop owner can *listen to* in their own language and immediately act on: **Do I qualify? What do I get? What must I do, and by when?**

Pipeline in one line:
`official document → structured understanding → personal eligibility verdict → plain-language voice explainer in a regional language`

**Two audiences**
- **Citizens:** benefits, eligibility, "am I covered?"
- **Small businesses:** compliance, licences, tax/municipal rules, "what changes for me, and by when?"

Pick **one primary persona** for the demo and make the other a toggle.

---

## 2. Why this is not "just a chatbot" (our USP)

A chatbot summarizes. It does not know the user, cannot prove its claims, and stops at explanation.

| Chatbot gap | What we build |
|---|---|
| Explains the scheme, never decides for *this person* | **Eligibility-as-logic:** rules extracted as structured conditions, user answers a short interview, a deterministic engine returns yes/no/maybe with the deciding clause |
| Paraphrases with no proof | **Clause-level grounding:** every claim links to the exact source clause (tap to view original) |
| Text-first | **Voice-first output** in a regional language |
| Ends at explanation | **Action checklist:** documents, where to apply, deadline |
| Pull only (user must find the doc) | **Live ingestion** from official sources (stretch) |

**Core trio (must be excellent):** eligibility-as-logic + clause-level grounding + voice delivery.
**Extras (only if the core is stable):** action checklist, live source fetching, change detection, WhatsApp channel.

Example: *"Farmers with < 2 ha land and income < ₹1.5L get ₹6,000/yr. Apply before 31 March with Aadhaar and land records at the CSC."*
The system extracts `land_ha < 2`, `income < 150000`, asks the user those two questions by voice, returns a verdict citing the clause, then lists: Aadhaar, land records, CSC, 31 March.

---

## 3. Hackathon rubric and how we score on it

| Pillar | Pts | Our answer |
|---|---|---|
| Technical Architecture & Engineering Depth | 20 | Modular pipeline as a real state graph (LangGraph-style), custom RAG over clause-level chunks, typed schemas, clean layering |
| AI Reasoning & Agentic Execution | 25 | Extractor → **Verifier** (self-correcting loop) → deterministic eligibility engine; agent decides when to ask for more info or a clearer image; source attribution on every claim |
| Problem Relevance, Impact & USP | 25 | Civic/governance use case; USP table above |
| Live Demo & Robustness | 30 | Runs live, end to end, with graceful edge-case handling |

### Hard rules (disqualification risks)
- **No dummy data.** No hardcoded scheme rules, sample outputs, or fake users in the app. Everything is extracted live from real documents (e-Gazette, India Code, PIB, myScheme, data.gov.in). Judges should be able to hand us a document and answer the interview themselves.
- **Built during the hackathon window.** No reusing older projects. Libraries and boilerplate are fine; core logic must be written in the window.
- **Everyone can explain everything.** Each member must be able to walk through data flow and AI logic. Do not let one person (or the AI IDE) own a module nobody else understands.
- **Live demo only.** No pre-recorded video, no mockups.
- Do not ship cached "demo outputs" that could look pre-baked. Process documents live on stage.

---

## 4. Scope and priorities

**Priority order**
1. Reliable core pipeline with citations and verification
2. Robust live demo with edge-case handling
3. Live ingestion from official sources
4. Voice and regional language quality
5. WhatsApp channel

**Decisions still open**
- Team size and hours available
- Languages to commit to (suggest 2 to 3, done well, e.g. Hindi + one more)
- Primary persona: citizen or small business
- One-way explainer only, or voice follow-up questions (stretch)

**WhatsApp feasibility (free):** Meta's Cloud API provides a free test number (limited to verified recipient numbers), and replies inside the 24-hour window to a user-initiated chat are free. Cost is not the issue; time is (webhook setup, OGG/Opus audio conversion, voice-in STT). Build the web app as the primary demo; add WhatsApp as a thin wrapper only after the core is stable. Always keep the web demo as a fallback.

---

## 5. Architecture

### 5.1 Core design principle

> **The LLM extracts and explains. Deterministic code decides.**

The eligibility verdict comes from plain Python evaluating structured conditions, never from an LLM's opinion. This is our strongest guardrail against hallucination and our best answer to the rubric's "precision of reasoning" line.

### 5.2 Pipeline (state graph)

```
[Input: upload / image / URL / live fetch]
        │
        ▼
 1. INGEST ─────── fetch or accept file, detect type
        │
        ▼
 2. PARSE ──────── PDF text / OCR (vision LLM) → clean text with page refs
        │
        ▼
 3. CLAUSE INDEX ─ split into clauses with stable IDs, embed, store (RAG)
        │
        ▼
 4. EXTRACT ────── structured output: benefits, conditions, obligations,
        │          deadlines, required documents (each with clause_id + quote)
        ▼
 5. VERIFY ─────── second pass checks every item against its source clause
        │          mismatch → retry / drop / flag as uncertain  (loop, max N)
        ▼
 6. INTERVIEW ──── ask only the questions needed to evaluate the conditions
        │          (voice/text/buttons), validate answers
        ▼
 7. EVALUATE ───── deterministic rule engine → YES / NO / MAYBE + reasons
        │          each reason cites a clause_id
        ▼
 8. COMPOSE ────── persona-aware plain-language explainer + action checklist,
        │          every sentence tagged with its source clause_id
        ▼
 9. LOCALIZE ───── simplify + translate to target language (legal terms glossary)
        │
        ▼
10. VOICE ──────── TTS → audio (OGG/Opus for WhatsApp, MP3/WAV for web)
        │
        ▼
 [Output: audio + text + clause citations + checklist]
```

Edge branches (these are scored): unreadable image → ask for a retake; document is not a policy → say so; contradictory or ambiguous clauses → flag as MAYBE with the reason; unsupported language → fall back; provider down → fallback provider or clear error.

### 5.3 Key data contracts (Pydantic models)

Define these first. Every module talks through them.

```python
class Clause:        id, text, page, doc_id
class Condition:     field, operator, value, unit, clause_id, quote
class Obligation:    description, deadline, required_documents[], clause_id, quote
class Benefit:       description, amount, frequency, clause_id, quote
class SchemeModel:   doc_id, title, audience, benefits[], conditions[], obligations[], confidence
class UserProfile:   dict of validated fields (age, income, land_ha, turnover, state, ...)
class Verdict:       status (YES|NO|MAYBE), reasons[ {condition, passed, clause_id} ], missing_fields[]
class Explainer:     segments[ {text, clause_ids[]} ], checklist[], language
```

`field` names should come from a controlled vocabulary (enum) so the interview and the engine agree on what "income" means.

### 5.4 Layers and dependency direction

```
api (routes)  →  services/agents  →  domain  ←  providers (LLM, TTS, STT, fetchers)
```

- **domain:** pure models and rule logic. No I/O, no framework imports. Fully unit-testable.
- **providers:** thin adapters behind interfaces (`LLMProvider`, `TTSProvider`, `Fetcher`). Swapping Gemini for another model or one TTS for another is a one-file change.
- **agents/services:** orchestration (the graph). Calls providers, produces domain objects.
- **api:** HTTP only. No business logic in routes.

Rule: arrows never point the other way. `domain` never imports from `providers` or `api`.

### 5.5 Suggested repo layout

```
project/
├── AGENTS.md                  # rules for the AI IDE (see section 6)
├── README.md
├── docs/ARCHITECTURE.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/               # routes: documents, interview, explain, webhooks
│   │   ├── core/              # config, logging, errors, retry utils
│   │   ├── domain/            # models.py, enums.py, field vocabulary
│   │   ├── ingestion/         # fetchers/ (egazette, pib, upload), parsers/ (pdf, image)
│   │   ├── indexing/          # chunker.py, vectorstore.py
│   │   ├── extraction/        # extractor.py, verifier.py, prompts/*.md
│   │   ├── eligibility/       # engine.py (deterministic), interview.py
│   │   ├── explain/           # composer.py, personas.py, glossary
│   │   ├── localize/          # translator.py, simplifier.py
│   │   ├── voice/             # tts.py, stt.py, audio.py (ffmpeg conversion)
│   │   ├── agents/            # graph.py, state.py, nodes/
│   │   └── providers/         # base.py (interfaces), gemini.py, tts_*.py
│   └── tests/
├── frontend/                  # thin UI: upload, interview, verdict, citations, audio
└── channels/whatsapp/         # webhook + media handling, wraps the same pipeline
```

### 5.6 Code-quality rules (this is what the 20-point pillar looks at)

1. **Typed everywhere.** Pydantic models at every boundary; type hints on every function.
2. **Structured LLM output only.** Force JSON against a schema, validate it, and retry on validation failure. Never parse free text with regex.
3. **Prompts live in files** (`extraction/prompts/*.md`), versioned, not buried in code strings.
4. **Providers behind interfaces.** One class per provider; the graph never imports an SDK directly.
5. **One responsibility per module.** If a file does two jobs, split it.
6. **Config via environment** (`core/config.py`). No keys or magic numbers in code.
7. **Resilience built in:** timeouts, retries with backoff, provider fallback, and typed custom errors that map to friendly API responses.
8. **Observability:** log a trace per run (node, input size, latency, retries). Expose this "reasoning trace" in the UI. It doubles as demo material for the agentic score.
9. **Latency awareness:** run independent steps concurrently (e.g. translate + start TTS per segment), stream progress to the UI.
10. **Tests where they pay off:** eligibility engine (all operators, missing fields, boundary values), verifier (catches a planted wrong extraction), chunker, and one end-to-end run on a real document. Test fixtures live in `tests/` only and must never be imported by app code (no-dummy-data rule).
11. **Honest uncertainty.** Low-confidence extractions surface as MAYBE or "please check the original", never as confident claims.

---

## 6. Working with Antigravity (AI IDE) without wrecking quality

- **Write the contracts yourself first:** `domain/models.py`, `providers/base.py`, and the graph state. Then let the agent fill in modules against those interfaces.
- **Add an `AGENTS.md` / workspace rules file** (use whichever rules mechanism Antigravity supports) containing: layer rules from 5.4, "no hardcoded or mock data in `app/`", "all LLM outputs validated against Pydantic", "prompts go in files", "add tests for every new domain function".
- **One module per task.** Small, reviewable prompts: "implement `eligibility/engine.py` against these models, with unit tests" beats "build the backend".
- **Read every diff.** The rules require every member to explain the code. If you cannot explain a function, rewrite or simplify it before moving on.
- **Watch for sneaky hardcoding.** AI agents love inserting sample data to make things "work". Grep for it before every commit.
- **Commit small and often.** It also gives a clean history showing the work happened during the hackathon window.
- **Keep a running `docs/ARCHITECTURE.md`** (a page with the diagram in 5.2 and the data contracts) so every teammate has the same mental model.

---

## 7. Suggested stack (adjust to team skills)

- **Backend:** Python, FastAPI, Pydantic, LangGraph (state graph), async I/O
- **LLM:** multimodal model with structured output (Gemini free tier is a reasonable start; keep it behind the provider interface)
- **Retrieval:** embeddings + a lightweight vector store (Chroma or FAISS) over clause chunks
- **OCR:** vision-capable LLM first; Tesseract as fallback
- **TTS/STT:** test Indian-language quality early (edge-tts, Google free tiers, Bhashini); convert audio with ffmpeg
- **Frontend:** a simple React/Next.js app (thin; judges look at the backend depth)
- **Channel (stretch):** WhatsApp Cloud API webhook

---

## 8. Build order (adapt to available hours)

1. **Contracts + skeleton:** domain models, provider interfaces, FastAPI app, config, logging
2. **Ingest + parse + clause index** on real documents
3. **Extract + verify loop** with clause citations (hardest, most valuable; spend time here)
4. **Eligibility engine + interview** (deterministic, well tested)
5. **Compose + localize + voice**
6. **UI:** upload → interview → verdict with tappable citations → audio player → trace panel
7. **Edge cases + failure handling** (see checklist below)
8. **Live source fetching** (stretch), then **WhatsApp** (stretch)
9. **Demo rehearsal** on real documents, on the actual venue network if possible

### Edge-case checklist (30 pts live)
- [ ] Blurry or rotated image
- [ ] Non-policy document uploaded
- [ ] Scanned PDF with no text layer
- [ ] Contradictory or ambiguous clauses
- [ ] User gives an invalid or out-of-range answer
- [ ] User skips a required question (verdict becomes MAYBE, not a guess)
- [ ] Very long document (chunking, latency)
- [ ] Unsupported language requested
- [ ] LLM/TTS provider timeout or rate limit (fallback + friendly message)
- [ ] Network drop during live demo (retry, clear status)

---

## 9. Demo script (2 to 3 minutes)

1. Fetch or upload a **real, fresh** notification live.
2. Show the extracted conditions with citations and the verifier catching or flagging something.
3. A judge answers the 2 to 3 interview questions themselves.
4. Verdict with the deciding clause highlighted in the original text.
5. Play the regional-language voice explainer and show the action checklist.
6. Deliberately upload a bad input to show graceful failure.
7. Show the reasoning trace panel.
