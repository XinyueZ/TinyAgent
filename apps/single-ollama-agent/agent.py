# suppress the warning
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

from dotenv import load_dotenv
from google.genai import types

from tiny_agent.agent.tiny_agent import TinyAgent
from tiny_agent.tools.decorator import *
from tiny_agent.tools.web.tools import google_search, tavily_search
from tiny_agent.utils.print_utils import format_text

load_dotenv()

_OLLAMA_CONFIG = {
    "host": os.environ.get(
        "OLLAMA_BASE_URL", os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    ),
}

_OLLAMA_MODEL = "glm-5:cloud"  # "glm-4.7-flash:latest" "qwen3:32b"  # glm-5:cloud "glm-4.7-flash:bf16" "qwen3:1.7b"#  "qwen3:8b" "qwen3:8b"
_OLLAMA_MODEL_CONFIG = {
    "think": "high",  # 'low', 'medium', 'high' or true, false
    "options": {
        "temperature": 0.5,
        "top_p": 0.5,
        "top_k": 10,
    },
    "keep_alive": -1,
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

Output:
At the end of the report, please also add a datetime to represent the time when the report was generated; use a separate section to place it.
Save the report to a file with the path "{output_path}".

**Reflect** on yourself to check if the report file exists. If not, redo the save operation to save the report to the file. If the file exists, response to user..

Response:
Read out the final report file as the response to the user.
"""


# python ./agent.py --output ./agent-output --tasks tasks/
if __name__ == "__main__":
    print("Deep Research Single Ollama Agent")
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

    # create the agent and run
    agent = TinyAgent(
        name="main_agent",
        model=_OLLAMA_MODEL,
        output_root=args.output,
        tools=[google_search, tavily_search],
        ollama_stuff={**_OLLAMA_MODEL_CONFIG, **_OLLAMA_CONFIG},
    )

    full_task = get_main_agent_goal(
        task=task, output_path=f"{agent.output_location}/result.md"
    )
    format_text(task, "⚑ Deep Research (single ollama agent)")
    result = agent(contents=full_task)
    format_text(result.message.content, "❀ Deep Research (single ollama agent) result")
