from typing import Dict, Any, Literal
from pydantic import BaseModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from app.core.llm import get_llm
from app.services.advisor.prompts import INPUT_GUARDRAIL_SYSTEM_PROMPT
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.input_guardrail")


class GuardrailOutput(BaseModel):
    status: Literal["safe", "unsafe"]


_REFUSAL_MESSAGES = {
    "unsafe": (
        "I'm unable to process that request. "
        "I'm here to assist you with personal finance and wealth management topics only. "
        "How can I help you with your financial goals?"
    )
}


async def input_guardrail_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Layer 1 Guardrail: Normal task powered by Vertex AI gemini-2.5-flash (low latency, deterministic).
    """
    session_id = config.get("configurable", {}).get("thread_id", "global") if config else "global"
    log = SessionLoggerAdapter(logger, session_id)
    log.info("── NODE: Input_Guardrail (Layer 1 Security - gemini-2.5-flash)")

    messages = state.get("messages", [])
    if not messages:
        log.warning("   No messages found in state for input guardrail check.")
        return {"guardrail_blocked": False}

    last_message = messages[-1]

    payload = [
        SystemMessage(content=INPUT_GUARDRAIL_SYSTEM_PROMPT),
        last_message,
    ]

    # Normal task model: gemini-2.5-flash via Vertex AI
    llm = get_llm(model_type="normal", temperature=0.0)
    structured_llm = llm.with_structured_output(GuardrailOutput)
    result: GuardrailOutput = await structured_llm.ainvoke(payload)

    status = result.status
    log.info(f"   Vertex AI Guardrail Check → status={status}")

    if status == "unsafe":
        log.warning("   ROUTE: BLOCKED → Short-circuit to Response_Generator")
        refusal_message = AIMessage(
            content=_REFUSAL_MESSAGES["unsafe"],
            additional_kwargs={"guardrail_status": "unsafe"},
        )
        return {
            "guardrail_blocked": True,
            "messages": [refusal_message],
        }

    log.info("   ROUTE: ALLOWED → Proceed to Intent_Classifier")
    return {"guardrail_blocked": False}
