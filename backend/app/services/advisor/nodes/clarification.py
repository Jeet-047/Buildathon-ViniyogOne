import time
from typing import Dict, Any
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from app.core.llm import get_llm
from app.services.advisor.prompts import CLARIFICATION_SYSTEM_PROMPT
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.clarification")


async def clarification_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Reasoning task: Powered by Vertex AI gemini-3.1-pro-preview to generate
    a sharp, goal-specific clarifying question (under 20 words).
    """
    session_id = config.get("configurable", {}).get("thread_id", "global") if config else "global"
    log = SessionLoggerAdapter(logger, session_id)
    log.info("── NODE: Clarification (Reasoning Task - gemini-3.1-pro-preview)")

    # Reasoning task model: gemini-3.1-pro-preview
    llm = get_llm(model_type="reasoning", temperature=0.0)

    messages = state.get("messages", [])
    behavioral_insights = state.get("behavioral_insights", {})

    context = ""
    signals = behavioral_insights.get("behavioral_signals", {})
    if signals:
        if signals.get("lifestyle_inflation_detected"):
            context += "\nContext: Lifestyle inflation has been detected."
        if signals.get("emergency_runway_months"):
            context += f"\nContext: Emergency runway is {signals['emergency_runway_months']:.1f} months."

    system_content = CLARIFICATION_SYSTEM_PROMPT + context
    payload = [SystemMessage(content=system_content)]
    payload.extend(messages[-3:])

    start_time = time.time()
    response = await llm.ainvoke(payload)
    duration = time.time() - start_time

    log.info(f"   Vertex AI Clarification prompt generated ({duration:.2f}s)")
    return {
        "messages": [response],
        "awaiting_clarification": True,
    }
