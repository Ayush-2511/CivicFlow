"""Session and Human-in-the-Loop Resume Routes."""

import asyncio
import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langgraph.types import Command

from app.graph import pipeline_graph
from app.routes.pipeline import get_or_create_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["Session"])


class SubmitAnswersRequest(BaseModel):
    answers: Dict[str, Any]
    units: Dict[str, str] = {}


@router.post("/{run_id}/answers")
async def submit_interview_answers(
    run_id: str,
    req: SubmitAnswersRequest,
) -> dict:
    """Submit interview answers to resume a paused pipeline run.

    Resumes the graph through evaluate, compose, and voice synthesis.
    """
    config = {"configurable": {"thread_id": run_id}}
    state_snap = pipeline_graph.get_state(config)

    if not state_snap or not state_snap.values:
        raise HTTPException(status_code=404, detail=f"No active session found for run_id '{run_id}'.")

    queue = get_or_create_queue(run_id)

    # Prepare resume payload
    resume_payload = {
        "answers": req.answers,
        "units": req.units,
    }

    try:
        # Resume graph execution with user submission
        async for event in pipeline_graph.astream(Command(resume=resume_payload), config=config):
            for node_name, node_output in event.items():
                logger.info("Resumed run %s completed node %s", run_id, node_name)
                trace = node_output.get("trace", [])
                latest_trace = trace[-1] if trace else {}

                await queue.put({
                    "type": "trace",
                    "node": node_name,
                    "status": node_output.get("status", "ok"),
                    "trace_entry": latest_trace,
                    "summary": latest_trace.get("details", ""),
                })

                if node_name == "voice" or node_output.get("status") == "completed":
                    explainer = node_output.get("explainer")
                    verdict = node_output.get("verdict")
                    await queue.put({
                        "type": "completed",
                        "run_id": run_id,
                        "verdict": verdict.model_dump() if verdict else None,
                        "explainer": explainer.model_dump() if explainer else None,
                    })

        # Fetch final completed state
        final_state = pipeline_graph.get_state(config)
        vals = final_state.values

        scheme = vals.get("scheme")
        verdict = vals.get("verdict")
        explainer = vals.get("explainer")

        return {
            "run_id": run_id,
            "status": vals.get("status", "completed"),
            "verdict": verdict.model_dump() if verdict else None,
            "explainer": explainer.model_dump() if explainer else None,
            "trace": vals.get("trace", []),
        }

    except Exception as e:
        logger.error("Failed to resume session for run %s: %s", run_id, str(e), exc_info=True)
        await queue.put({
            "type": "error",
            "run_id": run_id,
            "message": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Error resuming pipeline: {str(e)}") from e

