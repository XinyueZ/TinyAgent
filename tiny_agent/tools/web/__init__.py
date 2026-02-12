from .tavily_search import TavilySearch
from .google_search import GoogleSearch


def create_tavily_search(
    api_key: str,
    summarize_model: str,
    vertexai: bool,
    vertexai_project: str,
    vertexai_location: str,
    google_ai_studio_api_key: str,
    **kwargs,
) -> TavilySearch:
    return TavilySearch(
        api_key=api_key,
        summarize_model=summarize_model,
        vertexai=vertexai,
        vertexai_project=vertexai_project,
        vertexai_location=vertexai_location,
        google_ai_studio_api_key=google_ai_studio_api_key,
        **kwargs,
    )


def create_google_search(
    search_model: str,
    summarize_model: str,
    search_options: dict,
    summarize_options: dict,
) -> GoogleSearch:
    return GoogleSearch(
        search_model=search_model,
        summarize_model=summarize_model,
        **{
            "search_model_config": search_options,
            "summarize_model_config": summarize_options,
        },
    )
