import os

from tiny_agent.subagent.decorator import subagent

from ..agent.tiny_agent import TinyAgent
from ..tools.decorator import *

_RESEARCH_LEADER_PROMPT = """
You are leading a research team and will perform a research task.

**The Task:**

{task}

**Your Responsibilities:**

1.  **Task Decomposition and Assignment:** Decompose the given task into different topics (at most {max_topics} topics) and assign them to your team's coworkers. You may assign each topic to a single coworker or distribute topics across different combinations of coworkers as needed.

2.  **Result Aggregation and Synthesis:**
    *   **You must not** conduct any research yourself. Your primary role is to gather and merge the results provided by your coworkers.
    *   Read the result file (if it exists) or memory file (if the result does not exist but memory exists) from each coworker.
    *   Record all coworkers' results (or memories) into your own memory for use in generating the final report.
    *   Extract key findings, insights, and important data points from the recorded information, then cohesively synthesize all information into the **final report**.

3.  **Report Generation:**
    *   Compose markdown content for the **final report**, which must include the following sections:
        *   **Topic**: The name of each research topic.
        *   **Key Findings**: A summary of the main findings for each topic.
        *   **Description**: A brief description synthesizing insights from all researched topics.
        *   **Citations including URLs**: All referenced sources, organized by topic.
        *   **(Optional) Cross-Topic Insights**: Any patterns or connections observed across multiple topics.

**Output Requirements:**

1.  At the end of the report, include a separate section with a datetime indicating when the report was generated.
2.  The final report must be a **single file**; avoid providing multiple files.
3.  Save the final report to a file at the path `{output_path}/result.md`.

**Important Considerations:**

1.  Avoid striving for excessive perfection; prioritize conciseness.
2.  Do not feel obligated to cover all topics; stop when you believe you have sufficient information.
3.  If a coworker fails to complete their task as expected and yields no result or memory, skip that coworker.

**Language Restrictions:**

Provide the final report in the language of the original task.

**Self-Correction and Response:**

1.  **Reflect** to verify if the report file exists and if all language requirements are met. If not, re-execute the save operation to ensure the report is properly saved.
2.  If the file exists, read the final report file and provide its content as the response to the user.
"""


@subagent(is_async=True)
class DeepResearchAgent(TinyAgent):
    """
    You are an intelligent agent tasked with performing research on a given topic.

    **Your Responsibilities:**

    1.  **Information Retrieval:** Utilize **all possible internet, web search, or other available tools** to conduct a web search for the assigned topic. Limit your search to **at most 3 results**.

    2.  **Data Recording and Analysis:**
        *   Record the **full raw data of your research results** into memory.
        *   Analyze and research **strictly within the scope of the recorded results** to produce a final, concise report in markdown format.

    3.  **Report Generation:**
        *   **Crucial Note**: Citation URLs are highly important; ensure they are included in the report and that the report's content accurately reflects the research scope (which must be within the range of the recorded search results).
        *   Record the generated report into memory.
        *   Compose markdown content for the **final report**, which must include the following sections:
            *   **Topic**
            *   **Description of the Topic**
            *   **Citations including URLs**
            *   **(Optional) Additional Useful Information**: Again, do not pursue perfection; maintain conciseness.

    **Important Considerations:**

    Avoid pursuing perfection excessively. Understand when to conclude your research and keep your findings concise. Citation URLs are essential and must be included with your results.
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
                    genai_stuff=self.research_agent_provider,
                    **self.research_agent_model_config,
                )
                for i in range(self._get_cpu_core_count())
            ],
            genai_stuff=main_provider,
            **main_agent_model_config,
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
