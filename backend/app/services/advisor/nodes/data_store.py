from datetime import datetime, timezone
from typing import Dict, Any
from langchain_core.messages import message_to_dict
from langchain_core.runnables import RunnableConfig
from app.db.mongodb import get_mongo_db
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.data_store")


async def data_store_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Persists the updated conversation history and final state back to MongoDB Atlas
    under the 'conversations' collection, indexed by session_id and user_id.
    """
    session_id = config.get("configurable", {}).get("thread_id", "global") if config else "global"
    log = SessionLoggerAdapter(logger, session_id)
    log.info("── NODE: Data_Store")

    db = get_mongo_db()
    user_profile = state.get("user_profile", {})
    user_id = user_profile.get("user_id", "DEMO_YOUNGPRO_001")

    messages = state.get("messages", [])
    serializable_messages = [message_to_dict(msg) for msg in messages]

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.conversations.update_one(
            {"session_id": session_id},
            {"$set": {
                "session_id": session_id,
                "user_id": user_id,
                "messages": serializable_messages,
                "awaiting_clarification": state.get("awaiting_clarification", False),
                "updated_at": now_iso,
            }},
            upsert=True,
        )
        log.info(f"   Conversation state persisted to MongoDB Atlas (session_id={session_id}, user_id={user_id}, total_messages={len(serializable_messages)})")
    except Exception as exc:
        log.error(f"   ✗ MongoDB ERROR persisting conversation: {exc}")

    return state
