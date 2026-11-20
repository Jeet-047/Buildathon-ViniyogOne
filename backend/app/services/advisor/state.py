from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class FinanceAdvisorState(TypedDict):
    """
    Unified state schema for the Viniyog ONE Financial Advisory StateGraph workflow.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    user_profile: Dict[str, Any]
    behavioral_insights: Dict[str, Any]
    intent: str
    required_data: List[str]
    awaiting_clarification: bool
    guardrail_blocked: bool  # True if Layer 1 input guardrail blocked this turn
