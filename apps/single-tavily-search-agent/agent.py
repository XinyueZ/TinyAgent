# suppress the warning
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path
from tiny_agent.tools.decorator import *
from tiny_agent.agent.tiny_agent import TinyAgent
from tiny_agent.tools.web.tools import tavily_search, google_search

from google.genai import types
from dotenv import load_dotenv

load_dotenv()

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


def get_main_agent_goal(task: str, output_path: str) -> str:
    return f"""
You are leading a research and will perform a research task.

-----

The task:

{task}

-----

Decompose the task into piece of research topics and compile them into a list. 

Use the **all possible internet or web search tools** to perform a web search for each topic **ONE BY ONE**. Search for **at most 3 results** for each topic.
**Note**: Avoid pursuing perfection excessively. Know when to stop and keep it concise. Citation URLs are important; please carry them together with the results.
Record the **full raw data of research results** into memory.

Analyze and research **within the range of the recorded results** to produce a final but concise report.
**Note**: Citation URLs are important; please include them in the report and reflect the research range (must be within the range of the recorded search results). This is also sensitive.
Record the report into memory.

Compose markdown content based on the recorded report including the following sections:
- **Topic**: The name of each research topic
- **Key Findings**: A summary of the main findings for each topic
- **Description**: A brief description synthesizing insights from all researched topics
- **Citations including URLs**: All sources referenced, organized by topic
- (Optional) **Cross-Topic Insights**: Any patterns or connections observed across multiple topics

At the end of the report, please also add a datetime to represent the time when the report was generated; use a separate section to place it.
Save the report to a file with the path "{output_path}".

**Reflect** on yourself to check if the report file exists. If not, redo the save operation to save the report to the file. If the file exists, stop working.
"""


# python ./agent.py --output ./agent-output --tasks tasks/
if __name__ == "__main__":
    print("Single Tavily Search Agent")
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

    # create the agent and run
    agent = TinyAgent(
        name="main_agent",
        model=_MAIN_AGENT_MODEL,
        output_root=args.output,
        tools=[tavily_search, google_search],
        **{**_MAIN_AGENT_MODEL_CONFIG, **_PROVIDER_CONFIG},
    )

    agent(
        contents=get_main_agent_goal(
            task=task, output_path=f"{agent.output_location}/result.md"
        )
    )
