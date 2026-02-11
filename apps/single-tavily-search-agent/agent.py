# suppress the warning
import warnings
warnings.filterwarnings("ignore")

import os
from pathlib import Path
from tiny_agent.tools.decorator import *
from tiny_agent.agent.tiny_agent import TinyAgent
from tiny_agent.utils.tavily_search import TavilySearch
from apps import (
    PROVIDER_CONFIG,
    MAIN_AGENT_MODEL,
    MAIN_AGENT_MODEL_CONFIG,
    SUMMARIZE_MODEL,
    SUMMARIZE_MODEL_CONFIG,
)


def get_main_agent_goal(task: str, output_path: str) -> str:
    return f"""
You are leading a research and will perform a research task.

-----

The task:

{task}

-----

Decompose the task into piece of research topics and compile them into a list. 

Use the web_search tool to perform a web search for each topic **ONE BY ONE**. Search for **at most 3 results** for each topic.
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


@tool()
def web_search(query: str) -> str:
    """Perform a web search using Tavily API.

    Args:
        query: The search query to execute.

    Returns:
        A Python `str` with the following format:
        1. response: The search results with summaries
    """

    def _get_tavily_api_key_count() -> int:
        """Auto-calculate the number of TAVILY_API_KEY_ prefixed environment variables."""
        count = 0
        while os.getenv(f"TAVILY_API_KEY_{count}") is not None:
            count += 1
        return max(count, 1)

    api_key_count = _get_tavily_api_key_count()
    for i in range(5):
        try:
            key_index = int(os.environ.get("TAVILY_API_KEY_INDEX", 0))
            api_key = os.getenv(f"TAVILY_API_KEY_{key_index % api_key_count}")
            tavily_search = TavilySearch(
                api_key=api_key,
                summarize_model=SUMMARIZE_MODEL,
                **{**SUMMARIZE_MODEL_CONFIG, **PROVIDER_CONFIG},
            )
            os.environ["TAVILY_API_KEY_INDEX"] = str(key_index + 1)
            return tavily_search(query)
        except Exception as e:
            import traceback

            traceback.print_exc()
            return f"Failed to search. Error: {str(e)}, query: {query}"


# python ./agent.py --output ./agent-output
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--output", type=str, required=True, help="The output of the application"
    )
    parser.add_argument(
        "--tasks",
        type=str,
        required=False,
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
        model=MAIN_AGENT_MODEL,
        output_root=args.output,
        tools=[web_search],
        **{**MAIN_AGENT_MODEL_CONFIG, **PROVIDER_CONFIG},
    )
    
    agent(
        contents=get_main_agent_goal(
            task=task, output_path=f"{agent.output_location}/result.md"
        )
    )
