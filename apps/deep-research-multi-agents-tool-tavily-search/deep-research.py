# suppress the warning
import warnings
warnings.filterwarnings("ignore")

import os
from pathlib import Path
import time

from tiny_agent.tools.decorator import *
from tiny_agent.utils.tavily_search import TavilySearch
from apps import (
    PROVIDER_CONFIG,
    SUMMARIZE_MODEL,
    MAIN_AGENT_MODEL_CONFIG,
    MAIN_AGENT_MODEL,
    RESEARCH_AGENT_MODEL_CONFIG,
    RESEARCH_AGENT_MODEL,
    SUMMARIZE_MODEL_CONFIG,
    SUMMARIZE_MODEL,
)
from tiny_agent.use_cases.deep_research_multi_agents_tool import (
    DeepResearchMultAgentsTool,
)


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
    now_long_int = int(time.time())
    for i in range(3):
        try:
            key_index = (now_long_int + i) % api_key_count
            api_key = os.getenv(f"TAVILY_API_KEY_{key_index}")
            tavily_search = TavilySearch(
                api_key=api_key,
                summarize_model=SUMMARIZE_MODEL,
                **{**SUMMARIZE_MODEL_CONFIG, **PROVIDER_CONFIG},
            )
            return tavily_search(query)
        except Exception as e:
            import traceback

            traceback.print_exc()
            if i == 2:
                return f"Failed to search. Error: {str(e)}, query: {query}"


# python ./deep-research.py --output ./deep-research-output
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
    deep_research = DeepResearchMultAgentsTool(
        main_agent_model=MAIN_AGENT_MODEL,
        main_agent_model_config=MAIN_AGENT_MODEL_CONFIG,
        main_provider=PROVIDER_CONFIG,
        research_agent_model=RESEARCH_AGENT_MODEL,
        research_agent_model_config=RESEARCH_AGENT_MODEL_CONFIG,
        research_agent_provider=PROVIDER_CONFIG,
        output_root=args.output,
        research_tools=[web_search],
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
