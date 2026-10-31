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

from app.graph import checkpointer, pipeline_graph
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
                logger.info("Run %s completed node %s", run_id, node_name)
                trace = node_output.get("trace", [])
                latest_trace = trace[-1] if trace else {}

                await queue.put({
                    "type": "trace",
                    "node": node_name,
                    "status": node_output.get("status", "ok"),
                    "trace_entry": latest_trace,
                    "summary": latest_trace.get("details", ""),
                })

                # Check if paused for interview
                if node_name == "interview" and node_output.get("status") == "waiting_for_answers":
                    questions = node_output.get("questions", [])
                    await queue.put({
                        "type": "interview_required",
                        "run_id": run_id,
                        "questions": [q.model_dump() for q in questions],
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
            pass  # Already paused and notified

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

    return {
        "run_id": run_id,
        "status": vals.get("status", "processing"),
        "doc_id": vals.get("doc_id"),
        "next_nodes": list(state_snap.next),
        "is_paused": bool(state_snap.next and "interview" in state_snap.next),
        "questions": [q.model_dump() for q in vals.get("questions", [])],
        "trace": vals.get("trace", []),
        "scheme": scheme.model_dump() if scheme else None,
        "verdict": verdict.model_dump() if verdict else None,
        "explainer": explainer.model_dump() if explainer else None,
        "error": vals.get("error"),
    }

