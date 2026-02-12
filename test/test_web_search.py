import warnings

warnings.filterwarnings("ignore", category=UserWarning)

import os

import pytest
from dotenv import load_dotenv
from google.genai import types

from tiny_agent.tools.web import create_google_search, create_tavily_search


def _configs():
    load_dotenv()

    api_key = os.environ.get("TAVILY_API_KEY")

    search_model = "gemini-2.5-flash-lite"
    search_model_config = {
        "temperature": 1.0,
        "seed": 42,
        "top_p": 1.0,
        "top_k": 60,
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
        "vertexai_project": os.environ.get("GOOGLE_CLOUD_PROJECT", "hg-a1050-a7908707"),
        "google_ai_studio_api_key": os.environ.get("GOOGLE_AI_STUDIO_API_KEY", ""),
    }

    return (
        api_key,
        search_model,
        search_model_config,
        summarize_model,
        summarize_model_config,
        provider_config,
    )


def test_tavily_search_smoke():
    (
        api_key,
        _search_model,
        _search_model_config,
        summarize_model,
        summarize_model_config,
        provider_config,
    ) = _configs()

    if not api_key:
        pytest.skip("TAVILY_API_KEY is not set")

    searcher = create_tavily_search(
        api_key=api_key,
        summarize_model=summarize_model,
        **{**provider_config, **summarize_model_config},
    )
    result = searcher("what is Elon Musk's final goal on the Mars?")
    assert result


def test_google_search_smoke():
    (
        _api_key,
        search_model,
        search_model_config,
        summarize_model,
        summarize_model_config,
        provider_config,
    ) = _configs()

    searcher = create_google_search(
        search_model=search_model,
        summarize_model=summarize_model,
        search_options={**provider_config, **search_model_config},
        summarize_options={**provider_config, **summarize_model_config},
    )
    result = searcher("what is Elon Musk's final goal on the Mars?")
    assert result


def _manual_run():
    (
        api_key,
        search_model,
        search_model_config,
        summarize_model,
        summarize_model_config,
        provider_config,
    ) = _configs()

    print("=====Tavily Search=====")
    if api_key:
        tavily_searcher = create_tavily_search(
            api_key=api_key,
            summarize_model=summarize_model,
            **{**provider_config, **summarize_model_config},
        )
        print(tavily_searcher("what is Elon Musk's final goal on the Mars?"))
    else:
        print("Skipped (TAVILY_API_KEY is not set)")

    print("=====Google Search=====")
    google_searcher = create_google_search(
        search_model=search_model,
        summarize_model=summarize_model,
        search_options={**provider_config, **search_model_config},
        summarize_options={**provider_config, **summarize_model_config},
    )
    print(google_searcher("what is Elon Musk's final goal on the Mars?"))


if __name__ == "__main__":
    _manual_run()
