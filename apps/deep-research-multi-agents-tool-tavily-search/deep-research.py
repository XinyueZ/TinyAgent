# suppress the warning
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path
from tiny_agent.tools.decorator import *
from tiny_agent.tools.web.tools import tavily_search, google_search
from apps import (
    PROVIDER_CONFIG,
    MAIN_AGENT_MODEL_CONFIG,
    MAIN_AGENT_MODEL,
    RESEARCH_AGENT_MODEL_CONFIG,
    RESEARCH_AGENT_MODEL,
)
from tiny_agent.use_cases.deep_research_multi_agents_tool import (
    DeepResearchMultAgentsTool,
)


# python ./deep-research.py --output ./deep-research-output --tasks tasks/
if __name__ == "__main__":
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
        main_agent_model=MAIN_AGENT_MODEL,
        main_agent_model_config=MAIN_AGENT_MODEL_CONFIG,
        main_provider=PROVIDER_CONFIG,
        research_agent_model=RESEARCH_AGENT_MODEL,
        research_agent_model_config=RESEARCH_AGENT_MODEL_CONFIG,
        research_agent_provider=PROVIDER_CONFIG,
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
