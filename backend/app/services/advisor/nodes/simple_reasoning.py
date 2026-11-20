import time
from typing import Dict, Any
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from app.core.llm import get_llm
from app.services.advisor.prompts import SIMPLE_REASONING_SYSTEM_PROMPT
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.simple_reasoning")


async def simple_reasoning_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Handles simple conversational queries and greetings.
    Normal task powered by Vertex AI gemini-2.5-flash.
    """
    session_id = config.get("configurable", {}).get("thread_id", "global") if config else "global"
    log = SessionLoggerAdapter(logger, session_id)
    log.info("── NODE: Simple_Reasoning (gemini-2.5-flash)")

    # Normal task model: gemini-2.5-flash
    llm = get_llm(model_type="normal", temperature=0.7)

    messages = state.get("messages", [])
    user_profile = state.get("user_profile", {})
    user_name = user_profile.get("name")

    if user_name:
        system_instruction = f"User Information:\nName: {user_name}\n\n" + SIMPLE_REASONING_SYSTEM_PROMPT
    else:
        system_instruction = SIMPLE_REASONING_SYSTEM_PROMPT

    payload = [SystemMessage(content=system_instruction)]
    payload.extend(messages[-5:])

    start_time = time.time()
    response = await llm.ainvoke(payload)
    duration = time.time() - start_time

    log.info(f"   Vertex AI Simple Response generated ({duration:.2f}s)")
    return {"messages": [response]}
