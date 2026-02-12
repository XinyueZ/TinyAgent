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


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from google.genai import types

    # suppress warnings
    import warnings

    warnings.filterwarnings("ignore")

    load_dotenv()

    #
    # place some .env file or config environment variables
    #
    api_key = os.environ.get("TAVILY_API_KEY_8")

    search_model = "gemini-2.5-flash-lite"
    search_model_config = {
        "temperature": 0.0,
        "seed": 42,
        "thinking_config": types.ThinkingConfig(
            thinking_budget=0,
            include_thoughts=False,
        ),
    }

    summarize_model = "gemini-2.5-flash-lite"
    summarize_model_config = {
        "temperature": 0.0,
        "seed": 42,
        "thinking_config": types.ThinkingConfig(
            thinking_budget=0,
            include_thoughts=False,
        ),
    }

    provider_config = {
        "vertexai": bool(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", True)),
        "vertexai_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4"),
        "vertexai_project": os.environ.get(
            "GOOGLE_CLOUD_PROJECT", "hg-a1050-ai-ft-exp-pr-1234"
        ),
        "google_ai_studio_api_key": os.environ.get("GOOGLE_AI_STUDIO_API_KEY", ""),
    }

    print("=====Tavily Search=====")
    travily_searcher = create_tavily_search(
        api_key=api_key,
        summarize_model=summarize_model,
        **{**provider_config, **summarize_model_config},
    )
    print(travily_searcher("what is Elon Musk's final goal on the Mars?"))

    print("=====Google Search=====")
    google_searcher = create_google_search(
        search_model=search_model,
        summarize_model=summarize_model,
        search_options={**provider_config, **search_model_config},
        summarize_options={**provider_config, **summarize_model_config},
    )
    print(google_searcher("what is Elon Musk's final goal on the Mars?"))
