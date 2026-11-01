"""LangGraph State Graph Orchestrator for CivicFlow.

Wires all pipeline nodes into a state machine with pause/resume support,
conditional routing, trace logging, and checkpointer persistence.
"""

import logging
import time
from typing import Any, Dict, List, Optional, TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

from app.config import settings
from app.exceptions import CivicFlowError, NotAPolicy, ProviderError, UnreadableDocument
from app.nodes.compose import compose_explainer
from app.nodes.evaluate import evaluate
from app.nodes.extract import extract_scheme
from app.nodes.index import split_into_clauses
from app.nodes.ingest import ingest_document
from app.nodes.interview import generate_interview_questions, validate_answer
from app.nodes.parse import parse_document
from app.nodes.verify import verify_scheme
from app.nodes.voice import synthesize_explainer_voice
from app.providers.base import LLM, TTS
from app.providers.groq import GroqLLMProvider
from app.providers.llm import GeminiLLMProvider
from app.providers.speech import EdgeTTSProvider
from app.schemas import (
    AudienceType,
    Clause,
    Explainer,
    Field_,
    InterviewQuestion,
    Scheme,
    TraceEntry,
    UserProfile,
    Verdict,
)
from app.store import store

logger = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    """Universal state maintained across all nodes of the state graph."""
    run_id: str
    file_bytes: Optional[bytes]
    filename: str
    content_type: str
    url: Optional[str]
    doc_id: str
    persona: str                        # "citizen" | "business"
    language: str                       # e.g., "hi", "en", "mr"

    pages: List[Any]
    clauses: List[Clause]
    scheme: Optional[Scheme]

    questions: List[InterviewQuestion]
    profile: UserProfile
    user_units: Dict[str, str]
    user_answers: Dict[str, Any]

    verdict: Optional[Verdict]
    explainer: Optional[Explainer]

    status: str                         # "processing", "waiting_for_answers", "completed", "error"
    error: Optional[str]
    trace: List[Dict[str, Any]]
    verify_retries: int


# Shared checkpointer and graph instances
checkpointer = MemorySaver()
_default_llm: Optional[LLM] = None
_default_tts: Optional[TTS] = None


def get_llm() -> LLM:
    global _default_llm
    provider = (settings.LLM_PROVIDER or "groq").lower().strip()
    if provider == "groq" or (settings.GROQ_API_KEY and not settings.GEMINI_API_KEY):
        if not isinstance(_default_llm, GroqLLMProvider) or not _default_llm.api_key:
            _default_llm = GroqLLMProvider(api_key=settings.GROQ_API_KEY)
    elif _default_llm is None:
        _default_llm = GeminiLLMProvider()
    return _default_llm


def get_tts() -> TTS:
    global _default_tts
    if _default_tts is None:
        _default_tts = EdgeTTSProvider()
    return _default_tts


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

async def node_ingest(state: PipelineState) -> Dict[str, Any]:
    """Ingest file bytes or URL, compute SHA-256 doc_id, check cache."""
    t0 = time.perf_counter()
    try:
        result = await ingest_document(
            file_bytes=state.get("file_bytes"),
            filename=state.get("filename", "document.pdf"),
            url=state.get("url"),
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "ingest",
            "status": "ok",
            "ms": elapsed_ms,
            "details": f"Doc ID: {result.doc_id[:10]}... (cached={result.is_cached})",
        }
        return {
            "doc_id": result.doc_id,
            "filename": result.filename,
            "content_type": result.content_type,
            "file_bytes": result.raw_bytes,
            "status": "ingested",
            "trace": (state.get("trace") or []) + [trace_entry],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {"node": "ingest", "status": "error", "ms": elapsed_ms, "details": str(e)}
        return {
            "status": "error",
            "error": str(e),
            "trace": (state.get("trace") or []) + [trace_entry],
        }


async def node_parse(state: PipelineState) -> Dict[str, Any]:
    """Parse PDF or OCR image into PageText objects."""
    t0 = time.perf_counter()
    try:
        pages = await parse_document(
            raw_bytes=state["file_bytes"],
            content_type=state["content_type"],
            llm=get_llm(),
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "parse",
            "status": "ok",
            "ms": elapsed_ms,
            "details": f"Parsed {len(pages)} page(s), {sum(len(p.text) for p in pages)} characters",
        }
        return {
            "pages": pages,
            "status": "parsed",
            "trace": (state.get("trace") or []) + [trace_entry],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {"node": "parse", "status": "error", "ms": elapsed_ms, "details": str(e)}
        return {
            "status": "error",
            "error": str(e),
            "trace": (state.get("trace") or []) + [trace_entry],
        }


async def node_index(state: PipelineState) -> Dict[str, Any]:
    """Split page text into numbered clauses with stable IDs and persist to SQLite store."""
    t0 = time.perf_counter()
    try:
        doc_id = state["doc_id"]
        # Check if already cached in store
        cached = store.get_clauses(doc_id)
        if cached:
            clauses = cached
        else:
            clauses = split_into_clauses(state["pages"], doc_id)
            store.save_document(
                doc_id=doc_id,
                filename=state["filename"],
                content_type=state["content_type"],
                clauses=clauses,
            )

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "index",
            "status": "ok",
            "ms": elapsed_ms,
            "details": f"Indexed {len(clauses)} clauses with stable IDs",
        }
        return {
            "clauses": clauses,
            "status": "indexed",
            "trace": (state.get("trace") or []) + [trace_entry],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {"node": "index", "status": "error", "ms": elapsed_ms, "details": str(e)}
        return {
            "status": "error",
            "error": str(e),
            "trace": (state.get("trace") or []) + [trace_entry],
        }


async def node_extract(state: PipelineState) -> Dict[str, Any]:
    """Extract structured Scheme conditions, benefits, and obligations."""
    t0 = time.perf_counter()
    try:
        scheme = await extract_scheme(
            clauses=state["clauses"],
            doc_id=state["doc_id"],
            llm=get_llm(),
            verify=False,  # verify happens in next dedicated node
            run_id=state.get("run_id"),
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "extract",
            "status": "ok",
            "ms": elapsed_ms,
            "details": f"Extracted {len(scheme.conditions)} conditions, {len(scheme.benefits)} benefits",
        }
        return {
            "scheme": scheme,
            "status": "extracted",
            "trace": (state.get("trace") or []) + [trace_entry],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {"node": "extract", "status": "error", "ms": elapsed_ms, "details": str(e)}
        return {
            "status": "error",
            "error": str(e),
            "trace": (state.get("trace") or []) + [trace_entry],
        }


async def node_verify(state: PipelineState) -> Dict[str, Any]:
    """Self-correcting verification of extracted facts against original clauses."""
    t0 = time.perf_counter()
    try:
        raw_scheme = state["scheme"]
        assert raw_scheme is not None
        verified_scheme = await verify_scheme(
            scheme=raw_scheme,
            clauses=state["clauses"],
            llm=get_llm(),
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "verify",
            "status": "ok",
            "ms": elapsed_ms,
            "details": f"Verified with {int(verified_scheme.confidence * 100)}% confidence ({len(verified_scheme.uncertain)} unverified)",
        }
        retries = state.get("verify_retries", 0)
        return {
            "scheme": verified_scheme,
            "status": "verified",
            "verify_retries": retries + 1,
            "trace": (state.get("trace") or []) + [trace_entry],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {"node": "verify", "status": "error", "ms": elapsed_ms, "details": str(e)}
        return {
            "status": "error",
            "error": str(e),
            "trace": (state.get("trace") or []) + [trace_entry],
        }


async def node_interview(state: PipelineState) -> Dict[str, Any]:
    """Generate minimal interview questions and pause (interrupt) if answers are needed."""
    t0 = time.perf_counter()
    scheme = state["scheme"]
    assert scheme is not None
    profile = state.get("profile") or UserProfile()
    language = state.get("language", "hi")

    questions = generate_interview_questions(scheme, profile, language=language)

    # If all fields are already answered or no conditions exist, proceed immediately
    if not questions:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "interview",
            "status": "ok",
            "ms": elapsed_ms,
            "details": "All fields already satisfied in profile",
        }
        return {
            "questions": [],
            "status": "interview_ready",
            "trace": (state.get("trace") or []) + [trace_entry],
        }

    # Pause execution via interrupt to collect human answers from the API/UI
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    trace_entry = {
        "node": "interview",
        "status": "waiting_for_answers",
        "ms": elapsed_ms,
        "details": f"Waiting for {len(questions)} user answers: {[q.field.value for q in questions]}",
    }

    # interrupt pauses the graph. When resumed, user_answers returns the submitted payload.
    user_submission = interrupt({
        "type": "interview_required",
        "questions": [q.model_dump() for q in questions],
    })

    # When resumed, process and validate submitted answers
    updated_answers = dict(profile.answers)
    user_units = dict(state.get("user_units") or {})

    if isinstance(user_submission, dict):
        submitted_dict = user_submission.get("answers", user_submission)
        submitted_units = user_submission.get("units", {})

        for field_str, raw_val in submitted_dict.items():
            try:
                field_enum = Field_(field_str)
                is_valid, clean_val, _ = validate_answer(field_enum, raw_val)
                if is_valid:
                    updated_answers[field_enum] = clean_val
            except ValueError:
                pass

        for field_str, unit_val in submitted_units.items():
            try:
                field_enum = Field_(field_str)
                user_units[field_enum] = str(unit_val)
            except ValueError:
                pass

    updated_profile = UserProfile(answers=updated_answers)
    resumed_trace = {
        "node": "interview",
        "status": "ok",
        "ms": round((time.perf_counter() - t0) * 1000, 2),
        "details": f"Received {len(updated_answers)} validated answer(s)",
    }

    return {
        "questions": questions,
        "profile": updated_profile,
        "user_units": user_units,
        "status": "interview_completed",
        "trace": (state.get("trace") or []) + [trace_entry, resumed_trace],
    }


async def node_evaluate(state: PipelineState) -> Dict[str, Any]:
    """Pure Python deterministic rule evaluation engine."""
    t0 = time.perf_counter()
    try:
        scheme = state["scheme"]
        assert scheme is not None
        profile = state.get("profile") or UserProfile()
        user_units = state.get("user_units")

        verdict = evaluate(scheme, profile, user_units=user_units)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "evaluate",
            "status": "ok",
            "ms": elapsed_ms,
            "details": f"Deterministic Verdict: {verdict.status.value} ({verdict.summary})",
        }
        return {
            "verdict": verdict,
            "status": "evaluated",
            "trace": (state.get("trace") or []) + [trace_entry],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {"node": "evaluate", "status": "error", "ms": elapsed_ms, "details": str(e)}
        return {
            "status": "error",
            "error": str(e),
            "trace": (state.get("trace") or []) + [trace_entry],
        }


async def node_compose(state: PipelineState) -> Dict[str, Any]:
    """Compose localized voice explainer and action checklist."""
    t0 = time.perf_counter()
    try:
        scheme = state["scheme"]
        verdict = state["verdict"]
        assert scheme is not None and verdict is not None

        persona_str = state.get("persona", "citizen").lower()
        persona = AudienceType.BUSINESS if persona_str == "business" else AudienceType.CITIZEN
        language = state.get("language", "hi")

        explainer = await compose_explainer(
            scheme=scheme,
            verdict=verdict,
            persona=persona,
            language=language,
            llm=get_llm(),
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "compose",
            "status": "ok",
            "ms": elapsed_ms,
            "details": f"Composed {len(explainer.segments)} segments in {language}",
        }
        return {
            "explainer": explainer,
            "status": "composed",
            "trace": (state.get("trace") or []) + [trace_entry],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {"node": "compose", "status": "error", "ms": elapsed_ms, "details": str(e)}
        return {
            "status": "error",
            "error": str(e),
            "trace": (state.get("trace") or []) + [trace_entry],
        }


async def node_voice(state: PipelineState) -> Dict[str, Any]:
    """Synthesize speech for each segment in parallel and bind audio URLs."""
    t0 = time.perf_counter()
    try:
        explainer = state["explainer"]
        assert explainer is not None
        doc_id = state.get("doc_id", "unknown_doc")

        updated_explainer = await synthesize_explainer_voice(
            explainer=explainer,
            doc_id=doc_id,
            tts=get_tts(),
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {
            "node": "voice",
            "status": "ok",
            "ms": elapsed_ms,
            "details": f"Synthesized {len(updated_explainer.audio_urls)} audio segment(s)",
        }
        return {
            "explainer": updated_explainer,
            "status": "completed",
            "trace": (state.get("trace") or []) + [trace_entry],
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        trace_entry = {"node": "voice", "status": "error", "ms": elapsed_ms, "details": str(e)}
        return {
            "status": "completed",  # Don't fail the whole pipeline if TTS has a hiccup
            "error": f"Audio synthesis warning: {str(e)}",
            "trace": (state.get("trace") or []) + [trace_entry],
        }


# ---------------------------------------------------------------------------
# Routing logic (Conditional Edges)
# ---------------------------------------------------------------------------

def route_after_parse(state: PipelineState) -> str:
    """If document is unreadable or error occurred, abort early."""
    if state.get("status") == "error" or not state.get("pages"):
        return END
    return "index"


def route_after_index(state: PipelineState) -> str:
    if state.get("status") == "error":
        return END
    return "extract"


def route_after_extract(state: PipelineState) -> str:
    if state.get("status") == "error":
        return END
    return "verify"


def route_after_verify(state: PipelineState) -> str:
    """Proceed to interview. Uncertain claims are safely tracked for deterministic evaluation."""
    if state.get("status") == "error":
        return END
    return "interview"


def route_after_node(state: PipelineState) -> str:
    if state.get("status") == "error":
        return END
    return "continue"


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct and compile the state graph."""
    builder = StateGraph(PipelineState)

    builder.add_node("ingest", node_ingest)
    builder.add_node("parse", node_parse)
    builder.add_node("index", node_index)
    builder.add_node("extract", node_extract)
    builder.add_node("verify", node_verify)
    builder.add_node("interview", node_interview)
    builder.add_node("evaluate", node_evaluate)
    builder.add_node("compose", node_compose)
    builder.add_node("voice", node_voice)

    builder.set_entry_point("ingest")

    builder.add_edge("ingest", "parse")
    builder.add_conditional_edges("parse", route_after_parse, {"index": "index", END: END})
    builder.add_conditional_edges("index", route_after_index, {"extract": "extract", END: END})
    builder.add_conditional_edges("extract", route_after_extract, {"verify": "verify", END: END})
    builder.add_conditional_edges(
        "verify", route_after_verify, {"interview": "interview", END: END}
    )
    builder.add_edge("interview", "evaluate")
    builder.add_edge("evaluate", "compose")
    builder.add_edge("compose", "voice")
    builder.add_edge("voice", END)

    return builder.compile(checkpointer=checkpointer)


# Global compiled pipeline graph instance
pipeline_graph = build_graph()

