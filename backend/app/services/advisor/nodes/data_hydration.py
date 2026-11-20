from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from app.db.mongodb import get_mongo_db
from app.db.mock_data import resolve_user_id
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.data_hydration")


async def data_hydration_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Selectively hydrates user_profile and behavioral_insights from the database
    according to state['required_data'] determined by the intent classifier.
    """
    session_id = config.get("configurable", {}).get("thread_id", "global") if config else "global"
    log = SessionLoggerAdapter(logger, session_id)
    log.info("── NODE: Data_Hydration (Selective Retrieval)")

    db = get_mongo_db()
    user_profile = state.get("user_profile", {})
    raw_user_id = user_profile.get("user_id") or (config.get("configurable", {}).get("user_id") if config else "DEMO_YOUNGPRO_001")
    user_id = resolve_user_id(raw_user_id)

    required_data = state.get("required_data", [])
    log.info(f"   Hydrating data for user_id={user_id}: {required_data}")
    updates = {}

    # 1. Hydrate User Profile
    if "user_profile" in required_data:
        try:
            profile = await db.user_profiles.find_one({"user_id": user_id})
            if profile:
                demographics = profile.get("demographics", {})
                updates["user_profile"] = {**user_profile, "user_id": user_id, **demographics}
                log.info(f"   user_profile: ✓ LOADED for {user_id}")
            else:
                log.warning(f"   user_profile: ✗ NOT FOUND for {user_id}")
        except Exception as exc:
            log.error(f"   user_profile lookup error: {exc}")

    # 2. Hydrate Behavioral Insights
    if "behavioral_insights" in required_data:
        try:
            bi = await db.behavioral_insights.find_one({"user_id": user_id})
            if bi:
                bi_copy = dict(bi)
                bi_copy.pop("_id", None)
                updates["behavioral_insights"] = bi_copy
                log.info(f"   behavioral_insights: ✓ LOADED for {user_id}")
            else:
                log.warning(f"   behavioral_insights: ✗ NOT FOUND for {user_id}")
        except Exception as exc:
            log.error(f"   behavioral_insights lookup error: {exc}")

    return updates
