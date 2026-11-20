from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.services.advisor.state import FinanceAdvisorState
from app.services.advisor.nodes.ingest_context import ingest_context_node
from app.services.advisor.nodes.input_guardrail import input_guardrail_node
from app.services.advisor.nodes.intent_classifier import intent_classifier_node
from app.services.advisor.nodes.data_hydration import data_hydration_node
from app.services.advisor.nodes.simple_reasoning import simple_reasoning_node
from app.services.advisor.nodes.cognitive_reasoning import cognitive_reasoning_node
from app.services.advisor.nodes.clarification import clarification_node
from app.services.advisor.nodes.response_generator import response_generator_node
from app.services.advisor.nodes.data_store import data_store_node

memory_saver = MemorySaver()


def route_after_guardrail(state: FinanceAdvisorState) -> str:
    """
    Routes flow after Layer 1 Input Guardrail check.
    Unsafe queries short-circuit directly to Response_Generator.
    """
    if state.get("guardrail_blocked", False):
        return "blocked"
    return "allowed"


def route_user_intent(state: FinanceAdvisorState) -> str:
    """
    Routes flow based on classified user intent.
    """
    intent = state.get("intent", "chit_chat")
    if intent == "finance_advice":
        return "finance_advice"
    elif intent == "ambiguous":
        return "ambiguous"
    else:
        return "chit_chat"


def build_graph(checkpointer=None) -> StateGraph:
    """
    Builds and compiles the complete Viniyog ONE Financial Advisory StateGraph workflow.
    """
    graph = StateGraph(FinanceAdvisorState)

    # 1. Register Nodes
    graph.add_node("Ingest_Context", ingest_context_node)
    graph.add_node("Input_Guardrail", input_guardrail_node)
    graph.add_node("Intent_Classifier", intent_classifier_node)
    graph.add_node("Data_Hydration", data_hydration_node)
    graph.add_node("Simple_Reasoning", simple_reasoning_node)
    graph.add_node("Cognitive_Reasoning", cognitive_reasoning_node)
    graph.add_node("Clarification", clarification_node)
    graph.add_node("Response_Generator", response_generator_node)
    graph.add_node("Data_Store", data_store_node)

    # 2. Set Entry Point
    graph.set_entry_point("Ingest_Context")

    # 3. Static Flow Edges
    graph.add_edge("Ingest_Context", "Input_Guardrail")
    graph.add_edge("Data_Hydration", "Cognitive_Reasoning")
    graph.add_edge("Cognitive_Reasoning", "Response_Generator")
    graph.add_edge("Simple_Reasoning", "Response_Generator")
    graph.add_edge("Clarification", "Response_Generator")
    graph.add_edge("Response_Generator", "Data_Store")
    graph.add_edge("Data_Store", END)

    # 4. Conditional Edges: Layer 1 Guardrail (blocked -> Response_Generator | allowed -> Intent_Classifier)
    graph.add_conditional_edges(
        "Input_Guardrail",
        route_after_guardrail,
        {
            "blocked": "Response_Generator",
            "allowed": "Intent_Classifier",
        },
    )

    # 5. Conditional Edges: Intent Classifier Routing
    graph.add_conditional_edges(
        "Intent_Classifier",
        route_user_intent,
        {
            "chit_chat": "Simple_Reasoning",
            "finance_advice": "Data_Hydration",
            "ambiguous": "Clarification",
        },
    )

    # 6. Compile Graph with Checkpointer
    return graph.compile(checkpointer=checkpointer or memory_saver)
