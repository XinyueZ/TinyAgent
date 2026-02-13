# suppress the warning
from pickle import load
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path
from tiny_agent.tools.decorator import *
from tiny_agent.tools.web.tools import tavily_search, google_search
from tiny_agent.use_cases.deep_research_multi_agents_tool import (
    DeepResearchMultAgentsTool,
)

from google.genai import types
from dotenv import load_dotenv

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
    "vertexai": bool(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", True)),
    "vertexai_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4"),
    "vertexai_project": os.environ.get(
        "GOOGLE_CLOUD_PROJECT", "hg-hjghjg-ai-ft-exp-pr-hjjkhljhlhjkl"
    ),
    "google_ai_studio_api_key": os.environ.get("GOOGLE_AI_STUDIO_API_KEY", ""),
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

# python ./deep-research.py --output ./deep-research-output --tasks tasks/
if __name__ == "__main__":
    print("Deep Research Multi Agents Tool")
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
    deep_research = DeepResearchMultAgentsTool(
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
        task = "\n\n".join(
            [
                "## Task " + str(i) + ": " + open(file).read()
                for i, file in enumerate(Path(args.tasks).glob("**/*.md"))
            ]
        )
    else:
        # default tasks dir that at the same folder of this file
        tasks_dir = Path(__file__).parent / "tasks"
        if tasks_dir.exists():
            task = "\n\n".join(
                [
                    "## Task " + str(i) + ": " + open(file).read()
                    for i, file in enumerate(tasks_dir.glob("**/*.md"))
                ]
            )
        else:
            task = None

    if not task:
        raise ValueError("No tasks found")

    deep_research(task=task)
