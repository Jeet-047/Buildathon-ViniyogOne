import json
import time
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.db.mongodb import get_mongo_db
from app.db.mock_data import resolve_user_id
from app.schemas.requests import ChatPayload
from app.services.advisor.compiler import compiled_graph
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.api.chat")
router = APIRouter(prefix="/chat", tags=["Financial Advisory Chat"])


@router.post("/stream", status_code=status.HTTP_200_OK)
async def stream_chat_handler(payload: ChatPayload, db=Depends(get_mongo_db)):
    """
    Streaming Server-Sent Events (SSE) endpoint for multi-tenant financial chat.
    Streams AI responses token/chunk-wise, handles HITL interruptions,
    and attaches SEBI compliance metadata.
    """
    user_id = resolve_user_id(payload.user_id)
    session_id = payload.session_id
    log = SessionLoggerAdapter(logger, session_id)
    
    query_snippet = payload.message[:70] + ("..." if len(payload.message) > 70 else "")
    log.info(f"▶ STREAM START — user_id: {user_id} | message: '{query_snippet}'")

    start_time = time.time()
    graph_config = {
        "configurable": {
            "thread_id": session_id,
            "user_id": user_id,
        }
    }

    # Check if thread is suspended on a prior LangGraph interrupt (HITL)
    state = await compiled_graph.aget_state(graph_config)
    active_interrupts = []
    if state and state.tasks:
        for task in state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                active_interrupts.extend(task.interrupts)

    if active_interrupts:
        log.info("Thread has active interrupt — resuming with Command(resume=...)")
        graph_input = Command(resume={"answer": payload.message})
    else:
        graph_input = {
            "messages": [HumanMessage(content=payload.message)]
        }

    async def sse_event_stream_generator() -> AsyncGenerator[str, None]:
        try:
            intent_detected = None
            async for node_update_chunk in compiled_graph.astream(
                input=graph_input, config=graph_config, stream_mode="updates"
            ):
                # Track intent as it resolves
                if "Intent_Classifier" in node_update_chunk:
                    intent_detected = node_update_chunk["Intent_Classifier"].get("intent")

                # Send Response_Generator output
                if "Response_Generator" in node_update_chunk:
                    res_data = node_update_chunk["Response_Generator"]
                    if "messages" in res_data and res_data["messages"]:
                        assistant_msg = res_data["messages"][-1]
                        content = getattr(assistant_msg, "content", str(assistant_msg))

                        sse_payload = {
                            "content": content,
                            "intent": intent_detected,
                            "is_interrupt": False,
                        }

                        # Check for SEBI compliance disclaimer in metadata
                        disclaimer = getattr(assistant_msg, "additional_kwargs", {}).get("disclaimer")
                        if disclaimer:
                            sse_payload["disclaimer"] = disclaimer

                        guardrail_status = getattr(assistant_msg, "additional_kwargs", {}).get("guardrail_status")
                        if guardrail_status:
                            sse_payload["guardrail_status"] = guardrail_status

                        yield f"data: {json.dumps(sse_payload)}\n\n"

                await asyncio.sleep(0.01)

            # Post-run check: verify if execution suspended on a new interrupt
            post_run_state = await compiled_graph.aget_state(graph_config)
            new_interrupts = []
            if post_run_state and post_run_state.tasks:
                for task in post_run_state.tasks:
                    if hasattr(task, "interrupts") and task.interrupts:
                        new_interrupts.extend(task.interrupts)

            if new_interrupts:
                first_int = new_interrupts[0].value
                question = first_int.get("question") if isinstance(first_int, dict) else str(first_int)
                log.info(f"Execution paused on HITL interrupt question: '{question}'")
                yield f"data: {json.dumps({'content': question, 'is_interrupt': True})}\n\n"

            yield "data: [DONE]\n\n"

            total_duration = time.time() - start_time
            log.info(f"✅ STREAM COMPLETE — Duration: {total_duration:.2f}s")

        except Exception as err:
            total_duration = time.time() - start_time
            log.error(f"❌ STREAM FAILED after {total_duration:.2f}s: {err}")
            yield f"data: {json.dumps({'error': str(err)})}\n\n"

    return StreamingResponse(sse_event_stream_generator(), media_type="text/event-stream")


@router.post("", status_code=status.HTTP_200_OK)
async def chat_sync_handler(payload: ChatPayload, db=Depends(get_mongo_db)):
    """
    Standard synchronous (non-streaming) chat endpoint. Returns full JSON response.
    """
    user_id = resolve_user_id(payload.user_id)
    session_id = payload.session_id

    graph_config = {
        "configurable": {
            "thread_id": session_id,
            "user_id": user_id,
        }
    }

    state = await compiled_graph.aget_state(graph_config)
    has_interrupt = any(t.interrupts for t in state.tasks if hasattr(t, "interrupts")) if state and state.tasks else False

    if has_interrupt:
        graph_input = Command(resume={"answer": payload.message})
    else:
        graph_input = {"messages": [HumanMessage(content=payload.message)]}

    result = await compiled_graph.ainvoke(graph_input, config=graph_config)

    # Check for post-run interrupt
    post_state = await compiled_graph.aget_state(graph_config)
    new_intr = None
    if post_state and post_state.tasks:
        for t in post_state.tasks:
            if hasattr(t, "interrupts") and t.interrupts:
                val = t.interrupts[0].value
                new_intr = val.get("question") if isinstance(val, dict) else str(val)
                break

    if new_intr:
        return {
            "session_id": session_id,
            "content": new_intr,
            "is_interrupt": True,
        }

    messages = result.get("messages", [])
    last_msg = messages[-1] if messages else None
    content = getattr(last_msg, "content", "") if last_msg else ""
    disclaimer = getattr(last_msg, "additional_kwargs", {}).get("disclaimer") if last_msg else None
    guardrail_status = getattr(last_msg, "additional_kwargs", {}).get("guardrail_status") if last_msg else None

    return {
        "session_id": session_id,
        "content": content,
        "intent": result.get("intent"),
        "disclaimer": disclaimer,
        "guardrail_status": guardrail_status,
        "is_interrupt": False,
    }


@router.get("/history", status_code=status.HTTP_200_OK)
async def get_chat_history(
    session_id: str = Query(..., description="Browser session ID to retrieve chat history for"),
    db=Depends(get_mongo_db),
):
    """
    Fetches the persistent conversation history for a given session from MongoDB Atlas.
    Enables frontend to restore chat history when reloading or returning to a persona.
    """
    doc = await db.conversations.find_one({"session_id": session_id}, {"_id": 0})
    if not doc:
        return {
            "session_id": session_id,
            "messages": [],
            "total": 0,
        }

    raw_messages = doc.get("messages", [])
    formatted_messages = []
    for msg in raw_messages:
        role = "user" if msg.get("type") == "human" else "assistant"
        data = msg.get("data", {})
        content = data.get("content", "")
        additional_kwargs = data.get("additional_kwargs", {})
        formatted_messages.append({
            "role": role,
            "content": content,
            "disclaimer": additional_kwargs.get("disclaimer"),
            "guardrail_status": additional_kwargs.get("guardrail_status"),
        })

    return {
        "session_id": session_id,
        "user_id": doc.get("user_id"),
        "messages": formatted_messages,
        "total": len(formatted_messages),
        "updated_at": doc.get("updated_at"),
    }
