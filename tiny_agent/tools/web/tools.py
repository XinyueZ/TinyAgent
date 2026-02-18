from . import create_tavily_search, create_google_search
from tiny_agent.tools.decorator import tool
import os
import time
import threading
import fcntl
from apps import (
    PROVIDER_CONFIG,
    SEARCH_AGENT_MODEL,
    SEARCH_AGENT_MODEL_CONFIG,
    SUMMARIZE_MODEL,
    SUMMARIZE_MODEL_CONFIG,
)

_tavily_key_lock = threading.Lock()


@tool()
def tavily_search(query: str) -> str:
    """Perform a web search using Tavily Search.

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

    counter_path = os.getenv(
        "TAVILY_KEY_COUNTER_FILE", "/tmp/tiny_agent_tavily_key_counter"
    )
    with _tavily_key_lock:
        os.makedirs(os.path.dirname(counter_path), exist_ok=True)
        with open(counter_path, "a+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                raw = f.read().strip()
                counter = int(raw) if raw else 0
                start_index = counter % api_key_count
                counter += 1
                f.seek(0)
                f.truncate()
                f.write(str(counter))
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    for i in range(3):
        try:
            key_index = (start_index + i) % api_key_count
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
