import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tiny_agent.subagent.decorator import subagent
from tiny_agent.patterns import NUM_RESEARCHER_RESULTS

from ..tools.decorator import *
from ..agent.tiny_agent import TinyAgent

_RESEARCH_LEADER_PROMPT = """
You are leading a research team and will perform a research task.

-----

The task:

{task}

-----

Decompose the task into different topics (at most {max_topics} topics) and assign them to your team coworkers.

Complete the task by assigning decomposed topics to your coworkers. You may assign each topic to a single coworker or distribute topics across different combinations of coworkers as needed.
**You must not** do any research yourself; instead, you must gather and merge the results from the different coworkers.
Read the result file (if it exists) or memory file (if the result does not exist but memory exists) of every coworker.
Record all coworkers' results (or memories) into your memory to use them later for generating a final report.

Extract the key findings, insights, and important data points from the recorded information and synthesize all information into the **final report** cohesively.
Compose markdown content based on the **final report** including the following sections:
- **Topic**: The name of each research topic
- **Key Findings**: A summary of the main findings for each topic
- **Description**: A brief description synthesizing insights from all researched topics
- **Citations including URLs**: All sources referenced, organized by topic
- (Optional) **Cross-Topic Insights**: Any patterns or connections observed across multiple topics

Output:
- At the end of the report, please also add a datetime to represent the time when the report was generated; use a separate section to place it.
- You should provide only **one file** as the final report; please avoid providing multiple files.
- Save the final report to a file at the path {output_path}/result.md.

Notice:
- Avoid striving for excessive perfection; focus on being concise. 
- Do not feel obligated to cover all topics; stop when you feel you have enough information.
- If a coworker cannot complete as expected and yields no result or memory, skip that coworker.

Language restrictions: 
Provide a final report in the language of the original task.

**Reflect** on yourself to check if the report file exists and the language requirements are met. If not, redo the save operation to save the report to the file. If the file exists, respond to the user.

Response:
Read the final report file and provide it as the response to the user.
"""


@subagent(is_async=True)
class DeepResearchAgent(TinyAgent):
    f"""An intelligent agent that performs research for a given topic.
    Use the **all possible internet or web search or other tools** to perform a web search for the topic. Search for **at most {NUM_RESEARCHER_RESULTS} results**.
    **Note**: Avoid pursuing perfection excessively. Know when to stop and keep it concise; just stop when you think it's enough. Citation URLs are important; please include them with the results.
    Record the **full raw data of research results** into memory.

    Analyze and research **within the range of the recorded results** to produce a final but concise report in markdown format.
    **Note**: Citation URLs are important; please include them in the report and reflect the research range (which must be within the range of the recorded search results). This is also critical.
    Record the report into memory.

    Compose markdown content based on the **final report** including the following sections:
    - **Topic**
    - **Description of the Topic**
    - **Citations including URLs**
    - (Optional) Some additional information you find useful, but again, don't pursue perfection—just keep it concise.
    """
    ...


class DeepAgentsResearch:
    """
    This is a multi-agent Deep Research application with subagents.
    Main agent dispatches tasks to sub-agents hierarchically, aka. Supervisor multi-agent system.
    """

    def __init__(
        self,
        main_agent_model: str,
        main_agent_model_config: dict,
        main_provider: dict,
        research_agent_model: str,
        research_agent_model_config: dict,
        research_agent_provider: dict,
        output_root: str,
        research_tools: list,
    ):
        """
        Initialize the DeepResearchTool.

        Args:
            main_agent_model: The model for the main agent.
            main_agent_model_config: The model configuration for the main agent.
            main_provider: The provider for the main agent.
            research_agent_model: The model for the research agent.
            research_agent_model_config: The model configuration for the research agent.
            research_agent_provider: The provider for the research agent.
            output_root: The root directory for output files.
            research_tools: The tools for the research agent.
        """

        if not main_agent_model:
            raise ValueError("main_agent_model is required")
        if not main_agent_model_config:
            raise ValueError("main_agent_model_config is required")
        if not main_provider:
            raise ValueError("main_provider is required")
        if not research_agent_model:
            raise ValueError("research_agent_model is required")
        if not research_agent_model_config:
            raise ValueError("research_agent_model_config is required")
        if not research_agent_provider:
            raise ValueError("research_agent_provider is required")
        if not output_root:
            raise ValueError("output_root is required")
        if not research_tools:
            raise ValueError("research_tools is required")

        self.research_tools = research_tools
        self.output_root = output_root

        self.research_agent_model = research_agent_model
        self.research_agent_model_config = research_agent_model_config
        self.research_agent_provider = research_agent_provider

        self.main_agent = TinyAgent(
            name="lead_researcher",
            model=main_agent_model,
            output_root=output_root,
            subagents=[
                DeepResearchAgent(
                    name=f"cowork_researcher_{i}",
                    model=self.research_agent_model,
                    output_root=self.output_root,
                    tools=self.research_tools,
                    genai_stuff={
                        **self.research_agent_model_config,
                        **self.research_agent_provider,
                    },
                )
                for i in range(self._get_cpu_core_count())
            ],
            genai_stuff={**main_agent_model_config, **main_provider},
        )

    def _get_cpu_core_count(self):
        return os.cpu_count() or 1

    def __call__(self, task: str, **kwargs):
        """
        Execute the deep research task.

        Args:
            task: The task to execute.
            **kwargs: Additional keyword arguments to pass to the main agent, it shall update model config in the agent.
        """
        if not task:
            raise ValueError("Text that describes a task is required")

        output_path = f"{self.main_agent.output_location}/result.md"
        return self.main_agent(
            contents=_RESEARCH_LEADER_PROMPT.format(
                task=task,
                max_topics=f"{self._get_cpu_core_count()}",
                output_path=output_path,
                **kwargs,
            )
        )
