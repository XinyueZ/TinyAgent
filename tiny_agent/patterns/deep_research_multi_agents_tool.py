import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tiny_agent.patterns import NUM_RESEARCHER_RESULTS

from ..tools.decorator import *
from ..agent.tiny_agent import TinyAgent

_RESEARCH_LEADER_PROMPT = """
You are leading a research team and will perform a research task.

-----

The task:

{task}

-----

Decompose the task into different topics (at most {max_topics} topics) and compile them into a list. 
Conduct thorough research on the list **ONLY ONCE**. 
Avoid striving for excessive perfection, and focus on being concise. 
Do not feel obligated to cover all topics; stop when you feel you have enough information.

**You don't do** any research yourself; instead, you must merge the results from the different research sources.
Read the result file (if it exists) or memory file (if the result does not exist but memory exists) for each topic after the research.

Extract the key findings, insights, and important data points from each result and synthesize all extracted information into a cohesive **final report**.
If a topic cannot be researched and yields no result or memory, skip that topic.

Compose markdown content based on the **final report** including the following sections:
- **Topic**: The name of each research topic
- **Key Findings**: A summary of the main findings for each topic
- **Description**: A brief description synthesizing insights from all researched topics
- **Citations including URLs**: All sources referenced, organized by topic
- (Optional) **Cross-Topic Insights**: Any patterns or connections observed across multiple topics

Output:
At the end of the report, please also add a datetime to represent the time when the report was generated; use a separate section to place it.
Save the report to a file at the path "{output_path}".

**Reflect** on yourself to check if the report file exists. If not, redo the save operation to save the report to the file. If the file exists, response to user..

Response:
Read out the final report file as the response to the user.
"""

_RESEARCHER_PROMPT = """
Your task is to conduct deep research on the topic: {topic}.

Use the **all possible internet or web search tools** to perform a web search for the topic. Search for **at most {num_results} results**.
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

Save the report to a file at the path "{output_path}".

**Reflect** on yourself to check if the report file exists. If it does not, redo the save operation to save the report to the file. If the file exists, stop working.
"""


class DeepResearchMultAgentsTool:
    """
    This is a multi-agent Deep Research application based on direct tool use (aka. the Tool appears in the class name) and powered by multi-threading.
    Main agent uses the tool to start sub-agents hierarchically, aka. Supervisor multi-agent system.
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
            tools=[self._create_deep_research_tool()],
            genai_stuff=main_provider,
            **main_agent_model_config,
        )

    def _get_cpu_core_count(self):
        return os.cpu_count() or 1

    def _create_deep_research_tool(self):
        """Factory function to create a deep_research tool with output_path bound via closure."""

        @tool()
        def deep_research_on_topics(topics: list[str]) -> list[tuple[str, str]] | str:
            """
            Perform deep research on the given topics, which represent a list of different research questions.
            Search the internet to find relevant information.
            Use the findings to provide a concise and comprehensive answer.
            However, avoid pursuing perfection excessively. Keep it concise and to the point.

            Args:
                topics: The topics to research. A Python **list** of `str` containing the **research topics**.

            Returns:
                A Python list of `tuple`, where each tuple contains the topic and the full file path of the result in the filesystem.
                1. response: A tuple where the 1st element is the topic and the 2nd element is the result file path.
                2. If no topics is given, a text will be return with "We have no topics to start research. Please provide some topics as list to start research".
            """
            if not topics:
                return "We have no topics to start research. Please provide some topics as list to start research."

            def _run_agent(idx: int, topic: str) -> tuple[str, str]:
                sub_agent = TinyAgent(
                    name=f"researcher_{idx}",
                    model=self.research_agent_model,
                    output_root=self.output_root,
                    tools=self.research_tools,
                    genai_stuff=self.research_agent_provider,
                    **self.research_agent_model_config,
                )
                output_path = f"{sub_agent.output_location}/result.md"
                sub_agent(
                    contents=_RESEARCHER_PROMPT.format(
                        topic=topic,
                        output_path=output_path,
                        num_results=NUM_RESEARCHER_RESULTS,
                    )
                )
                return (topic, output_path)

            with ThreadPoolExecutor(
                max_workers=min(len(topics), self._get_cpu_core_count())
            ) as executor:
                futures = {
                    executor.submit(_run_agent, i, t): t for i, t in enumerate(topics)
                }
                result_tuples = []
                for future in as_completed(futures):
                    topic = futures[future]
                    try:
                        result_tuples.append(future.result())
                    except Exception as e:
                        import traceback

                        traceback.print_exc()
                        result_tuples.append((topic, str(e)))

            # Verify result files exist; fall back to memory.md or a placeholder message
            verified_tuples = []
            for topic, result_path in result_tuples:
                if Path(result_path).exists():
                    verified_tuples.append((topic, result_path))
                else:
                    memory_path = Path(result_path).parent / "memory.md"
                    if memory_path.exists():
                        verified_tuples.append((topic, str(memory_path)))
                    else:
                        verified_tuples.append(
                            (
                                topic,
                                "No result has been generated, please **ignore** this topic research.",
                            )
                        )
            return verified_tuples

        return deep_research_on_topics

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
