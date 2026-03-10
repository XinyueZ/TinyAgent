# suppress the warning
import warnings

warnings.filterwarnings("ignore")

import os
from pathlib import Path

from dotenv import load_dotenv
from google.genai import types

from tiny_agent.patterns.swarm_agent import SwarmAgent
from tiny_agent.tools.web.tools import google_search, tavily_search
from tiny_agent.utils.print_utils import format_text

load_dotenv()

_PROVIDER_CONFIG = {
    "vertexai": os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True") == "True",
    "vertexai_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4"),
    "vertexai_project": os.environ.get(
        "GOOGLE_CLOUD_PROJECT", "hg-hjghjg-ai-ft-exp-pr-hjjkhljhlhjkl"
    ),
    "google_ai_studio_api_key": os.environ.get(
        "GOOGLE_AI_STUDIO_API_KEY", "adfasdfasdfads"
    ),
}

_AGENT_STARTER_MODEL = "gemini-3-flash-preview"
_AGENT_STARTER_MODEL_CONFIG = {
    "temperature": 1.0,
    "seed": 42,
    "top_p": 1.0,
    "top_k": 60,
    "thinking_config": types.ThinkingConfig(
        thinking_level=types.ThinkingLevel.HIGH,
        include_thoughts=False,
    ),
}

# For google search tool
_SEARCH_AGENT_MODEL = "gemini-3.1-flash-lite-preview"
_SEARCH_AGENT_MODEL_CONFIG = {
    "temperature": 1.0,
    "seed": 42,
    "top_p": 1.0,
    "top_k": 60,
    "thinking_config": types.ThinkingConfig(
        thinking_level=types.ThinkingLevel.HIGH,
        include_thoughts=False,
    ),
}

# For all web search tools
_SUMMARIZE_MODEL = "gemini-3.1-flash-lite-preview"
_SUMMARIZE_MODEL_CONFIG = {
    "temperature": 0.0,
    "seed": 42,
    "thinking_config": types.ThinkingConfig(
        thinking_level=types.ThinkingLevel.MINIMAL,
        include_thoughts=False,
    ),
}


tavily_search.summarize_model = _SUMMARIZE_MODEL
tavily_search.summarize_model_config = _SUMMARIZE_MODEL_CONFIG
tavily_search.provider_config = _PROVIDER_CONFIG


google_search.search_model = _SEARCH_AGENT_MODEL
google_search.summarize_model = _SUMMARIZE_MODEL
google_search.search_options = {**_SEARCH_AGENT_MODEL_CONFIG, **_PROVIDER_CONFIG}
google_search.summarize_options = {**_SUMMARIZE_MODEL_CONFIG, **_PROVIDER_CONFIG}


# python ./swarm-agent.py --output ./swarm-agent-output --tasks tasks/
if __name__ == "__main__":
    print("Deep Research Swarm Agent")
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--output", type=str, required=True, help="The output of the application"
    )
    parser.add_argument(
        "--tasks",
        type=str,
        required=True,
        help="The directory of tasks, md or txt files",
    )
    args = parser.parse_args()
    if args.tasks:
        task_files = list(Path(args.tasks).glob("*.md")) + list(
            Path(args.tasks).glob("*.txt")
        )
        task = "\n\n".join(
            [
                "## Task " + str(i) + ": " + open(file).read()
                for i, file in enumerate(task_files)
            ]
        )
    else:
        # default tasks dir that at the same folder of this file
        tasks_dir = Path(__file__).parent / "tasks"
        if tasks_dir.exists():
            task_files = list(tasks_dir.glob("*.md")) + list(tasks_dir.glob("*.txt"))
            task = "\n\n".join(
                [
                    "## Task " + str(i) + ": " + open(file).read()
                    for i, file in enumerate(task_files)
                ]
            )
        else:
            task = None

    if not task:
        raise ValueError("No tasks found")

    team = SwarmAgent(
        output=args.output,
        model=_AGENT_STARTER_MODEL,
        model_config=_AGENT_STARTER_MODEL_CONFIG,
        provider=_PROVIDER_CONFIG,
        tools=[tavily_search, google_search],
    )
    format_text(
        task,
        "⚑ Deep Research (swarm agent), flexible style collaboration among agents to complete the task",
        "green",
    )

    result = team(task)

    format_text(
        result.text,
        "❀ Deep Research (swarm agent) result, flexible style collaboration among agents to complete the task",
        "green",
    )
