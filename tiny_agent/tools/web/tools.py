from . import create_tavily_search, create_google_search
from tiny_agent.tools.decorator import tool
import os
import threading
import fcntl
 

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

    missing = [
        name
        for name in ("summarize_model", "summarize_model_config", "provider_config")
        if not hasattr(tavily_search, name)
    ]
    if missing:
        print(f"Missing tool configuration attributes: {', '.join(missing)}")
        raise RuntimeError(
            f"Missing tool configuration attributes: {', '.join(missing)}. "
            "Please refer to the configuration in any app entry file under apps/ (the file where the app main lives)."
        )

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
            search = create_tavily_search(
                api_key=api_key,
                summarize_model=tavily_search.summarize_model,
                **{
                    **tavily_search.summarize_model_config,
                    **tavily_search.provider_config,
                },
            )
            return search(query)
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
    missing = [
        name
        for name in (
            "search_model",
            "summarize_model",
            "search_options",
            "summarize_options",
        )
        if not hasattr(google_search, name)
    ]
    if missing:
        print(f"Missing tool configuration attributes: {', '.join(missing)}")
        raise RuntimeError(
            f"Missing tool configuration attributes: {', '.join(missing)}. "
            "Please refer to the configuration in any app entry file under apps/ (the file where the app main lives)."
        )

    for _ in range(5):
        try:
            search = create_google_search(
                search_model=google_search.search_model,
                summarize_model=google_search.summarize_model,
                search_options=google_search.search_options,
                summarize_options=google_search.summarize_options,
            )
            return search(query)
        except Exception as e:
            import traceback

            traceback.print_exc()
            return f"Failed to search. Error: {str(e)}, query: {query}"
