from typing import List, Literal, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from app.core.llm import get_llm
from app.services.advisor.prompts import INTENT_CLASSIFIER_SYSTEM_PROMPT
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.intent_classifier")


class IntentClassifierOutput(BaseModel):
    intent: Literal["finance_advice", "chit_chat", "ambiguous"] = Field(
        ...,
        description="Classified intent of the user's latest query."
    )
    required_data: List[Literal[
        "user_profile",
        "behavioral_insights"
    ]] = Field(
        default_factory=list,
        description="Specific user models needed to answer the query: 'user_profile' and/or 'behavioral_insights'."
    )


async def intent_classifier_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Reasoning task: Powered by Vertex AI gemini-3.1-pro-preview for deep intent classification
    and required data determination.
    """
    session_id = config.get("configurable", {}).get("thread_id", "global") if config else "global"
    log = SessionLoggerAdapter(logger, session_id)
    log.info("── NODE: Intent_Classifier (Reasoning Task - gemini-3.1-pro-preview)")

    # Reasoning task model: gemini-3.1-pro-preview
    llm = get_llm(model_type="reasoning", temperature=0.0)
    structured_llm = llm.with_structured_output(IntentClassifierOutput)

    messages = state.get("messages", [])
    if not messages:
        log.warning("   No messages present for classification. Fallback to chit_chat.")
        return {"intent": "chit_chat", "required_data": []}

    awaiting_clarification = state.get("awaiting_clarification", False)
    window_size = 3 if awaiting_clarification else 5
    recent_messages = messages[-window_size:]

    classification_messages = [
        SystemMessage(content=INTENT_CLASSIFIER_SYSTEM_PROMPT)
    ]

    if awaiting_clarification:
        classification_messages.append(
            SystemMessage(content="Context: The system is currently waiting for the user to clarify their previous ambiguous query.")
        )

    classification_messages.extend(recent_messages)

    result: IntentClassifierOutput = await structured_llm.ainvoke(classification_messages)

    log.info(f"    Vertex AI Intent Result → intent={result.intent} | required_data={result.required_data}")

    return {
        "intent": result.intent,
        "required_data": result.required_data,
        "awaiting_clarification": False if awaiting_clarification else state.get("awaiting_clarification", False),
    }
