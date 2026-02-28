# suppress the warning
import warnings
from pickle import load

warnings.filterwarnings("ignore")
from pathlib import Path

from dotenv import load_dotenv
from google.genai import types

from tiny_agent.tools.decorator import *
from tiny_agent.tools.web.tools import google_search, tavily_search
from tiny_agent.patterns.deep_agents_research import DeepAgentsResearch
from tiny_agent.utils.print_utils import format_text

load_dotenv()

_RESEARCH_AGENT_MODEL = "gemini-2.5-flash-lite"
_RESEARCH_AGENT_MODEL_CONFIG = {
    "temperature": 1.0,
    "seed": 42,
    "top_p": 1.0,
    "top_k": 60,
    "thinking_config": types.ThinkingConfig(
        thinking_budget=-1,
        include_thoughts=False,
    ),
}

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

_MAIN_AGENT_MODEL = "gemini-3-flash-preview"
_MAIN_AGENT_MODEL_CONFIG = {
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
_SEARCH_AGENT_MODEL = "gemini-2.5-flash-lite"
_SEARCH_AGENT_MODEL_CONFIG = {
    "temperature": 1.0,
    "seed": 42,
    "top_p": 1.0,
    "top_k": 60,
    "thinking_config": types.ThinkingConfig(
        thinking_budget=-1,
        include_thoughts=False,
    ),
}

# For all web search tools
_SUMMARIZE_MODEL = "gemini-2.5-flash-lite"
_SUMMARIZE_MODEL_CONFIG = {
    "temperature": 0.0,
    "seed": 42,
    "thinking_config": types.ThinkingConfig(
        thinking_budget=0,
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


# python ./deep-research.py --output ./deep-research-output --tasks tasks/
if __name__ == "__main__":
    print("Deep Agents Research (multi sub-agents)")
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
    deep_research = DeepAgentsResearch(
        main_agent_model=_MAIN_AGENT_MODEL,
        main_agent_model_config=_MAIN_AGENT_MODEL_CONFIG,
        main_provider=_PROVIDER_CONFIG,
        research_agent_model=_RESEARCH_AGENT_MODEL,
        research_agent_model_config=_RESEARCH_AGENT_MODEL_CONFIG,
        research_agent_provider=_PROVIDER_CONFIG,
        output_root=args.output,
        research_tools=[tavily_search, google_search],
    )

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
    format_text(task, "⚑ Deep Agents Research (multi sub-agents)")
    result = deep_research(task=task)
    format_text(result.text, "❀ Deep Agents Research result")
