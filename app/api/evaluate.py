import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.models.request import EvaluateRequest
from app.services.account_agent_service import account_agent_service

router = APIRouter()


@router.post("/evaluate")
async def evaluate(request: EvaluateRequest):
    """Stream account evaluation events with SSE."""

    async def event_generator():
        async for event in account_agent_service.execute(request):
            yield {
                "event": "message",
                "data": json.dumps(event, ensure_ascii=False),
            }
            if event.get("type") in {"complete", "error"}:
                break

    return EventSourceResponse(
        event_generator(),
        sep="\n",
        ping=0,
    )

