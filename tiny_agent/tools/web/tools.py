from . import create_tavily_search, create_google_search
from tiny_agent.tools.decorator import tool
import os
import time
from apps import (
    PROVIDER_CONFIG,
    SEARCH_AGENT_MODEL,
    SEARCH_AGENT_MODEL_CONFIG,
    SUMMARIZE_MODEL,
    SUMMARIZE_MODEL_CONFIG,
)


@tool()
def tavily_search(query: str) -> str:
    """One kind of internt search approach, perform a web search using Tavily Search.

    Args:
        query: The search query to execute.

    Returns:
        A Python `str` with the following format:
        1. response: The search results with summaries
    """

    def _get_tavily_api_key_count() -> int:
        """Auto-calculate the number of TAVILY_API_KEY_ prefixed environment variables."""
        count = 0
        while os.getenv(f"TAVILY_API_KEY_{count}") is not None:
            count += 1
        return max(count, 1)

    api_key_count = _get_tavily_api_key_count()
    now_long_int = int(time.time())
    for i in range(3):
        try:
            key_index = (now_long_int + i) % api_key_count
            api_key = os.getenv(f"TAVILY_API_KEY_{key_index}")
            tavily_search = create_tavily_search(
                api_key=api_key,
                summarize_model=SUMMARIZE_MODEL,
                **{**SUMMARIZE_MODEL_CONFIG, **PROVIDER_CONFIG},
            )
            return tavily_search(query)
        except Exception as e:
            import traceback

            traceback.print_exc()
            if i == 2:
                return f"Failed to search. Error: {str(e)}, query: {query}"


@tool()
def google_search(query: str) -> str:
    """Perform internet/web search using Google Search.

    Args:
        query: The search query to execute.

    Returns:
        A Python `str` with the following format:
        1. response: The search results with summaries
    """
    for _ in range(5):
        try:
            google_search = create_google_search(
                search_model=SEARCH_AGENT_MODEL,
                summarize_model=SUMMARIZE_MODEL,
                search_options={**SEARCH_AGENT_MODEL_CONFIG, **PROVIDER_CONFIG},
                summarize_options={**SUMMARIZE_MODEL_CONFIG, **PROVIDER_CONFIG},
            )
            return google_search(query)
        except Exception as e:
            import traceback

            traceback.print_exc()
            return f"Failed to search. Error: {str(e)}, query: {query}"
