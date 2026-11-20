import os
import time
import httpx
from langchain_core.tools import tool
from langgraph.types import interrupt
from app.core.config import settings
from app.core.logger import get_logger

tool_logger = get_logger("advisor.tools")


@tool
async def web_search(query: str) -> str:
    """
    Search the web for real-time market data, stock prices, commodity/gold rates, or interest rates.
    Input should be a search query string.
    """
    tool_logger.info(f"   [TOOL] web_search triggered for query: '{query}'")
    tavily_key = settings.TAVILY_API_KEY or os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        tool_logger.warning("   [TOOL] web_search: TAVILY_API_KEY not configured. Returning market fallback.")
        return f"Real-time search unavailable. Note: As of current market indicators, please verify live benchmark indices and gold rates via official market exchanges."

    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 2,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

        duration = time.time() - start_time
        results = data.get("results", [])
        if not results:
            tool_logger.warning(f"   [TOOL] web_search: 0 results returned for '{query}' ({duration:.2f}s)")
            return f"No search results found for: '{query}'"

        tool_logger.info(f"   [TOOL] web_search: ✓ SUCCESS ({len(results)} results in {duration:.2f}s)")
        formatted = []
        for idx, r in enumerate(results, 1):
            title = r.get("title", "Market Update")
            url = r.get("url", "")
            content = r.get("content", "")
            formatted.append(f"Source [{idx}]: {title}\nURL: {url}\nContent: {content}")

        return "\n\n---\n\n".join(formatted)
    except Exception as exc:
        duration = time.time() - start_time
        tool_logger.error(f"   [TOOL] web_search: ✗ ERROR ({duration:.2f}s): {exc}")
        return f"Search service temporarily unavailable ({exc}). Using prevailing baseline figures."


@tool
async def request_human_input(question: str) -> str:
    """
    Use this tool to ask the user a specific question when you need more details or parameters 
    (e.g., loan interest rate, monthly expenses) to answer their query.
    Input MUST be a single, short, direct question.
    """
    tool_logger.info(f"   [TOOL] request_human_input triggered: '{question}'")
    # Native LangGraph interrupt halts graph execution and yields the question
    user_response = interrupt({"question": question})
    if isinstance(user_response, dict):
        return str(user_response.get("answer", user_response))
    return str(user_response)
