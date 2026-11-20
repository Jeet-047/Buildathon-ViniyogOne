from typing import Optional, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("core.llm")


def get_llm(
    model_type: Literal["normal", "reasoning"] = "normal",
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_output_tokens: Optional[int] = None,
) -> ChatGoogleGenerativeAI:
    """
    Factory function providing Gemini LLM instances via Vertex AI using Application Default Credentials (ADC).
    Uses ChatGoogleGenerativeAI with vertexai=True and location="global"
    
    Model Assignment:
    - Normal tasks (guardrail, simple chit-chat): gemini-2.5-flash
    - Reasoning tasks (intent classification, clarification, cognitive reasoning ReAct): gemini-3.1-pro-preview
    
    Args:
        model_type: "normal" for gemini-2.5-flash or "reasoning" for gemini-3.1-pro-preview.
        model: Explicit model name override.
        temperature: Sampling temperature.
        max_output_tokens: Maximum tokens in response.
    """
    # 1. Resolve model name
    if model:
        selected_model = model
    elif model_type == "reasoning":
        selected_model = settings.GOOGLE_REASONING_MODEL
    else:
        selected_model = settings.GOOGLE_NORMAL_MODEL

    logger.info(
        f"Instantiating ChatGoogleGenerativeAI(model='{selected_model}', vertexai=True, "
        f"location='{settings.GOOGLE_VERTEX_LOCATION}', temp={temperature})"
    )

    kwargs = {
        "model": selected_model,
        "vertexai": True,
        "location": settings.GOOGLE_VERTEX_LOCATION or "global",
        "temperature": temperature,
    }

    if settings.GOOGLE_CLOUD_PROJECT:
        kwargs["project"] = settings.GOOGLE_CLOUD_PROJECT

    if max_output_tokens:
        kwargs["max_output_tokens"] = max_output_tokens

    return ChatGoogleGenerativeAI(**kwargs)
