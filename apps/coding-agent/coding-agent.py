import warnings

warnings.filterwarnings("ignore")

import os
from pathlib import Path

from google.genai import types

from tiny_agent.agent.tiny_coding_agent import TinyCodingAgent
from tiny_agent.tools.decorator import *
from tiny_agent.tools import CODING_TOOLS

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

_PYTHON_CODING_AGENT_MODEL = "gemini-3-flash-preview"
_PYTHON_CODING_AGENT_MODEL_CONFIG = {
    "temperature": 1.0,
    "seed": 42,
    "top_p": 1.0,
    "top_k": 60,
    "thinking_config": types.ThinkingConfig(
        thinking_level=types.ThinkingLevel.HIGH,
        include_thoughts=False,
    ),
}

# python ./coding-agent.py --output ./coding-agent-output  --deps ./requirements.txt --coding-tools ./coding-tools.txt --tasks tasks/
if __name__ == "__main__":
    print("Coding Agent")
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--output", type=str, required=True, help="The output of the application"
    )
    parser.add_argument(
        "--deps",
        type=str,
        required=False,
        help="The path to the requirements.txt file",
    )
    parser.add_argument(
        "--coding-tools",
        type=str,
        required=False,
        help="The path to the coding tools file",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        required=True,
        help="The directory of tasks, md or txt files",
    )
    args = parser.parse_args()

    perf_libs = []
    if args.deps:
        with open(args.deps, "r") as f:
            perf_libs = f.read().splitlines()

    coding_tools = []
    if args.coding_tools:
        with open(args.coding_tools, "r") as f:
            coding_tools = f.read().splitlines()
            # coding_tools:
            # get_stock_data
            # get_currency_exchange_rate
            # ...
            coding_tools = [CODING_TOOLS[tool] for tool in coding_tools]

    agent = TinyCodingAgent(
        name="python-coding-agent",
        model=_PYTHON_CODING_AGENT_MODEL,
        output_root=args.output,
        perf_libs=perf_libs,
        coding_tools=coding_tools,
        genai_stuff={**_PYTHON_CODING_AGENT_MODEL_CONFIG, **_PROVIDER_CONFIG},
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

    format_text(task, "⚑ Coding Agent")
    result = agent(contents=task)
    format_text(result.text, "❀ Coding Agent result")
