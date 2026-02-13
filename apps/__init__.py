import os
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

############## AI part ##############
PROVIDER_CONFIG = {
    "vertexai": bool(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", True)),
    "vertexai_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4"),
    "vertexai_project": os.environ.get(
        "GOOGLE_CLOUD_PROJECT", "hg-hjghjg-ai-ft-exp-pr-hjjkhljhlhjkl"
    ),
    "google_ai_studio_api_key": os.environ.get("GOOGLE_AI_STUDIO_API_KEY", ""),
}

SEARCH_AGENT_MODEL = "gemini-2.5-flash-lite"
SEARCH_AGENT_MODEL_CONFIG = {
    "temperature": 1.0,
    "seed": 42,
    "top_p": 1.0,
    "top_k": 60,
    "thinking_config": types.ThinkingConfig(
        thinking_budget=-1,
        include_thoughts=False,
    ),
}

SUMMARIZE_MODEL = "gemini-2.5-flash-lite"
SUMMARIZE_MODEL_CONFIG = {
    "temperature": 0.0,
    "seed": 42,
    "thinking_config": types.ThinkingConfig(
        thinking_budget=0,
        include_thoughts=False,
    ),
}
