"""Pipeline Execution and Server-Sent Events (SSE) Routes."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command

from app.graph import checkpointer, pipeline_graph, get_llm, get_tts
from app.nodes.compose import compose_explainer
from app.nodes.extract import EXTRACTION_PROGRESS
from app.nodes.interview import generate_interview_questions
from app.nodes.voice import synthesize_explainer_voice
from app.providers.sources import sources_fetcher
from app.schemas import AudienceType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

# In-memory event stream queues per run_id
RUN_EVENT_QUEUES: Dict[str, asyncio.Queue] = {}
RUN_METADATA: Dict[str, Dict[str, Any]] = {}


def get_or_create_queue(run_id: str) -> asyncio.Queue:
    if run_id not in RUN_EVENT_QUEUES:
        RUN_EVENT_QUEUES[run_id] = asyncio.Queue()
    return RUN_EVENT_QUEUES[run_id]


async def _run_graph_in_background(run_id: str, initial_state: dict) -> None:
    """Execute LangGraph pipeline in background, streaming events into the run's SSE queue."""
    queue = get_or_create_queue(run_id)
    config = {"configurable": {"thread_id": run_id}}

    try:
        await queue.put({
            "type": "run_started",
            "run_id": run_id,
            "filename": initial_state.get("filename"),
            "language": initial_state.get("language"),
        })

        async for event in pipeline_graph.astream(initial_state, config=config):
            for node_name, node_output in event.items():
                logger.info("Run %s event for node %s", run_id, node_name)

                # Special handling for LangGraph interrupt event
                if node_name == "__interrupt__":
                    questions = []
                    if isinstance(node_output, (list, tuple)) and len(node_output) > 0:
                        intr = node_output[0]
                        intr_val = getattr(intr, "value", intr)
                        if isinstance(intr_val, dict):
                            questions = intr_val.get("questions", [])
                    elif isinstance(node_output, dict):
                        questions = node_output.get("questions", [])

                    logger.info("Run %s paused at interview with %d questions", run_id, len(questions))
                    await queue.put({
                        "type": "interview_required",
                        "run_id": run_id,
                        "questions": questions,
                    })
                    continue

                if not isinstance(node_output, dict):
                    continue

                trace = node_output.get("trace", [])
                latest_trace = trace[-1] if trace else {}

                await queue.put({
                    "type": "trace",
                    "node": node_name,
                    "status": node_output.get("status", "ok"),
                    "trace_entry": latest_trace,
                    "summary": latest_trace.get("details", ""),
                    "latency_ms": latest_trace.get("ms"),
                })

                # Check if paused for interview
                if node_name == "interview" and node_output.get("status") == "waiting_for_answers":
                    questions = node_output.get("questions", [])
                    await queue.put({
                        "type": "interview_required",
                        "run_id": run_id,
                        "questions": [q.model_dump() if hasattr(q, "model_dump") else q for q in questions],
                    })

                # Check if completed
                if node_name == "voice" or node_output.get("status") == "completed":
                    explainer = node_output.get("explainer")
                    verdict = node_output.get("verdict")
                    await queue.put({
                        "type": "completed",
                        "run_id": run_id,
                        "verdict": verdict.model_dump() if verdict else None,
                        "explainer": explainer.model_dump() if explainer else None,
                    })

        # Final check if pipeline paused
        state_snap = pipeline_graph.get_state(config)
        if state_snap.next and "interview" in state_snap.next:
            questions = []
            if state_snap.tasks:
                for task in state_snap.tasks:
                    interrupts = getattr(task, "interrupts", [])
                    for intr in interrupts:
                        intr_val = getattr(intr, "value", intr)
                        if isinstance(intr_val, dict) and "questions" in intr_val:
                            questions.extend(intr_val["questions"])

            if questions:
                await queue.put({
                    "type": "interview_required",
                    "run_id": run_id,
                    "questions": questions,
                })

    except Exception as e:
        logger.error("Error executing pipeline for run %s: %s", run_id, str(e), exc_info=True)
        await queue.put({
            "type": "error",
            "run_id": run_id,
            "message": str(e),
        })


class StartUrlRequest(BaseModel):
    url: str
    persona: str = "citizen"
    language: str = "hi"


@router.post("/start")
async def start_pipeline(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    persona: str = Form("citizen"),
    language: str = Form("hi"),
) -> dict:
    """Start pipeline run with uploaded PDF/image or official URL."""
    if file is None and not url:
        raise HTTPException(status_code=400, detail="Either a file upload or a URL must be provided.")

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    file_bytes: Optional[bytes] = None
    filename: str = "document.pdf"
    content_type: str = "application/pdf"

    if file:
        file_bytes = await file.read()
        filename = file.filename or "upload.pdf"
        content_type = file.content_type or "application/pdf"

    initial_state = {
        "run_id": run_id,
        "file_bytes": file_bytes,
        "filename": filename,
        "content_type": content_type,
        "url": url,
        "persona": persona.lower(),
        "language": language.lower(),
        "status": "started",
        "trace": [],
        "verify_retries": 0,
    }

    RUN_METADATA[run_id] = {
        "run_id": run_id,
        "filename": filename,
        "url": url,
        "persona": persona,
        "language": language,
    }

    # Launch state graph in background
    asyncio.create_task(_run_graph_in_background(run_id, initial_state))

    return {
        "run_id": run_id,
        "status": "started",
        "stream_url": f"/pipeline/{run_id}/events",
        "status_url": f"/pipeline/{run_id}/status",
    }


@router.post("/start-json")
async def start_pipeline_json(req: StartUrlRequest) -> dict:
    """Alternative JSON body endpoint for starting a run from a URL."""
    return await start_pipeline(url=req.url, persona=req.persona, language=req.language)


@router.get("/{run_id}/events")
async def stream_pipeline_events(run_id: str):
    """Server-Sent Events (SSE) stream emitting real-time progress for a run."""
    queue = get_or_create_queue(run_id)

    async def event_generator():
        while True:
            try:
                # Wait for next event with a periodic heartbeat
                msg = await asyncio.wait_for(queue.get(), timeout=20.0)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                if msg.get("type") in ["completed", "error"]:
                    break
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive
                yield f": ping\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}/status")
async def get_pipeline_status(run_id: str) -> dict:
    """Get current snapshot of pipeline state from checkpointer."""
    config = {"configurable": {"thread_id": run_id}}
    state_snap = pipeline_graph.get_state(config)

    if not state_snap or not state_snap.values:
        meta = RUN_METADATA.get(run_id)
        if not meta:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        return {"run_id": run_id, "status": "initializing", "metadata": meta}

    vals = state_snap.values
    scheme = vals.get("scheme")
    verdict = vals.get("verdict")
    explainer = vals.get("explainer")

    # Extract pending interview questions if graph is paused at interrupt
    questions = []
    is_paused = False
    if state_snap.tasks:
        for task in state_snap.tasks:
            interrupts = getattr(task, "interrupts", [])
            for intr in interrupts:
                intr_val = getattr(intr, "value", intr)
                if isinstance(intr_val, dict) and "questions" in intr_val:
                    questions.extend(intr_val["questions"])
                    is_paused = True

    if not questions:
        raw_q = vals.get("questions", [])
        questions = [q.model_dump() if hasattr(q, "model_dump") else q for q in raw_q]

    status = "waiting_for_answers" if is_paused else vals.get("status", "processing")
    if verdict:
        status = "completed"

    return {
        "run_id": run_id,
        "status": status,
        "doc_id": vals.get("doc_id"),
        "progress": EXTRACTION_PROGRESS.get(run_id) or EXTRACTION_PROGRESS.get(vals.get("doc_id", "")),
        "next_nodes": list(state_snap.next),
        "is_paused": is_paused,
        "questions": questions,
        "trace": vals.get("trace", []),
        "scheme": scheme.model_dump() if scheme else None,
        "verdict": verdict.model_dump() if verdict else None,
        "explainer": explainer.model_dump() if explainer else None,
        "error": vals.get("error"),
    }


class SwitchLanguageRequest(BaseModel):
    language: str


@router.post("/{run_id}/switch-language")
async def switch_language(run_id: str, req: SwitchLanguageRequest) -> dict:
    """Dynamically switch language and regenerate localized explainer & regional voice without reloading."""
    config = {"configurable": {"thread_id": run_id}}
    state_snap = pipeline_graph.get_state(config)

    if not state_snap or not state_snap.values:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    vals = state_snap.values
    scheme = vals.get("scheme")
    verdict = vals.get("verdict")
    persona_str = vals.get("persona", "citizen")
    persona = AudienceType.BUSINESS if persona_str == "business" else AudienceType.CITIZEN
    new_lang = req.language.lower().strip()

    new_explainer = None
    if scheme and verdict:
        # Re-compose explainer in target language
        new_explainer = await compose_explainer(
            scheme=scheme,
            verdict=verdict,
            persona=persona,
            language=new_lang,
            llm=get_llm(),
        )
        # Re-synthesize speech in target language
        doc_id = vals.get("doc_id", "unknown_doc")
        new_explainer = await synthesize_explainer_voice(
            explainer=new_explainer,
            doc_id=doc_id,
            tts=get_tts(),
            language=new_lang,
        )

    # Regenerate interview questions in new language
    questions = []
    if scheme:
        profile = vals.get("profile")
        questions = generate_interview_questions(scheme, profile, language=new_lang)

    # Update state in checkpointer
    updated_values = {"language": new_lang}
    if new_explainer:
        updated_values["explainer"] = new_explainer
    if questions:
        updated_values["questions"] = questions

    pipeline_graph.update_state(config, updated_values)

    # Broadcast language switch to active SSE listeners
    queue = RUN_EVENT_QUEUES.get(run_id)
    if queue:
        await queue.put({
            "type": "language_switched",
            "run_id": run_id,
            "language": new_lang,
            "explainer": new_explainer.model_dump() if new_explainer else None,
            "questions": [q.model_dump() for q in questions],
        })

    return {
        "run_id": run_id,
        "language": new_lang,
        "explainer": new_explainer.model_dump() if new_explainer else None,
        "questions": [q.model_dump() for q in questions],
    }
