from typing import Dict, Any
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.services.advisor.guardrails import apply_output_guardrails
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.response_generator")


async def response_generator_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Normalizes, cleans, and applies Layer 2 Output Guardrails (brand sanitization & SEBI disclaimer).
    """
    session_id = config.get("configurable", {}).get("thread_id", "global") if config else "global"
    log = SessionLoggerAdapter(logger, session_id)
    log.info("── NODE: Response_Generator (Layer 2 Output Guardrails)")

    messages = state.get("messages", [])
    if not messages:
        log.warning("   No messages found in state.")
        return {}

    last_message = messages[-1]

    if isinstance(last_message, AIMessage):
        content = last_message.content

        # 1. Normalize list-based content blocks into a single string
        if isinstance(content, list):
            parts = []
            for chunk in content:
                if isinstance(chunk, dict):
                    parts.append(chunk.get("text", ""))
                else:
                    parts.append(str(chunk))
            content_str = "".join(parts)
        else:
            content_str = str(content)

        cleaned_content = content_str.strip()

        # 2. Apply Layer 2 output guardrail only for finance_advice
        intent = state.get("intent")
        is_final_advice = (intent == "finance_advice")

        disclaimer = None
        if is_final_advice:
            cleaned_content, disclaimer = apply_output_guardrails(cleaned_content)
            if disclaimer:
                log.info("   Output Guardrail: is_final_advice=True → SEBI disclaimer attached to metadata")
            else:
                log.info("   Output Guardrail: is_final_advice=True → No disclaimer keyword matched")
        else:
            log.info("   Output Guardrail: Not final advice → skipping disclaimer")

        # 3. Attach disclaimer cleanly to additional_kwargs (NEVER in message body)
        existing_kwargs = dict(getattr(last_message, "additional_kwargs", {}) or {})
        if disclaimer:
            existing_kwargs["disclaimer"] = disclaimer

        normalized_message = AIMessage(
            content=cleaned_content,
            id=getattr(last_message, "id", None) or "final_response",
            response_metadata=getattr(last_message, "response_metadata", {}),
            usage_metadata=getattr(last_message, "usage_metadata", None),
            additional_kwargs=existing_kwargs,
        )

        log.info(f"   Response normalized (length={len(cleaned_content)} chars)")
        return {"messages": [normalized_message]}

    log.info("   Last message was not AIMessage — passing through.")
    return {}
