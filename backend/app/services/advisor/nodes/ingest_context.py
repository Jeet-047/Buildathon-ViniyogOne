from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from app.db.mock_data import resolve_user_id
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.ingest_context")


async def ingest_context_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Graph Entry Point (Node 1): Ingests the incoming request, resolves the persona/user identifier,
    and initializes state defaults with zero external database latency.
    
    Database hydration for 'user_profile' and 'behavioral_insights' is handled
    selectively downstream in the Data_Hydration node only when needed.
    """
    configurable = config.get("configurable", {}) if config else {}
    session_id = configurable.get("thread_id", "global")
    log = SessionLoggerAdapter(logger, session_id)

    raw_user_id = configurable.get("user_id", "DEMO_YOUNGPRO_001")
    user_id = resolve_user_id(raw_user_id)
    log.info(f"── NODE: Ingest_Context | user_id resolved: {user_id} (from '{raw_user_id}')")

    existing_profile = state.get("user_profile") or {}

    return {
        "messages": state.get("messages", []),
        "user_profile": {**existing_profile, "user_id": user_id},
        "behavioral_insights": state.get("behavioral_insights") or {},
        "intent": state.get("intent") or "chit_chat",
        "required_data": state.get("required_data") or [],
        "awaiting_clarification": state.get("awaiting_clarification") or False,
        "guardrail_blocked": False,
    }
