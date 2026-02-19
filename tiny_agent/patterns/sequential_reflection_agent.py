from typing import Callable

from tiny_agent.agent.tiny_agent import TinyAgent
from tiny_agent.subagent.decorator import subagent


class AgentStarter(TinyAgent):
    """
    You are the starter for an AI task.
    Your mission is to decompose the task into subtasks and transfer them **together as a bundle** to the sibling responsible for regression and analysis.
    """

    ...


@subagent(is_async=False)
class AgentRegressionAndAnalysis(TinyAgent):
    """
    You are responsible for performing regression and analysis on the information you receive.
    Conduct thorough research and analysis on the specified topics,
    and provide results that you consider credible and reliable.
    During this process, you may utilize any available web search or internet query tools to assist your analysis.
    **Always**: Keep it concise and avoid excessive perfectionism that wastes time. Aim for brevity.
    **Always transfer** your results to the sibling responsible for critical analysis for validation.

    In your results, please provide:
    - **Topic**: The name of each research topic
    - **Key Findings**: A summary of the main findings for each topic
    - **Description**: A brief description synthesizing insights from all researched topics
    - **Citations including URLs**: All sources referenced, organized by topic
    - (Optional) **Cross-Topic Insights**: Any patterns or connections observed across multiple topics
    
    Additionally you can expose the storage path of your reuslt to the sibling who will perform critical analysis.
    """

    ...


@subagent(is_async=False)
class AgentCriticalAnalysis(TinyAgent):
    """
    You are responsible for critiquing and validating the original results against user requirements from the sibling who performed regression and analysis.
    During this process, you may utilize any available web search or internet query tools to assist your critique and validation.
    After you finish your critique and validation, transfer your findings to the sibling responsible for **revision**.
    You must provide:
    1. Original results from the sibling who performed regression and analysis
    2. Your critique and validation
    3. Your argument for why the findings are correct or incorrect, and a request for revision **if needed**
    
    Additionally you can expose the storage path of your results to the sibling who will perform revision.
    Also you can expose the storage path of original results to the sibling who will perform revision.
    """

    ...


@subagent(is_async=False)
class AgentRevision(TinyAgent):
    """
    You are responsible for performing revisions (if needed) based on the critique and validation from the sibling who performed critical analysis.
    Provide your revised results that you consider credible and reliable.
    During this process, you may utilize any available web search or internet query tools to assist your analysis.
    **Always**: Keep it concise and avoid excessive perfectionism that wastes time. Aim for brevity.
    **Always transfer** all your revised results to the sibling who can compose the final report.

    In your results, please provide:
    - **Topic**: The name of each research topic
    - **Key Findings**: A summary of the main findings for each topic
    - **Description**: A brief description synthesizing insights from all researched topics
    - **Citations including URLs**: All sources referenced, organized by topic
    - (Optional) **Cross-Topic Insights**: Any patterns or connections observed across multiple topics
    
    Additionally you can expose the storage path of your results to the sibling who will compose the final report.
    """

    ...


@subagent(is_async=False)
class AgentComposeReport(TinyAgent):
    """
    You compose the report in markdown format based on the source, 
    respond to the user with the final report, 
    and save the report to the default result storage.
    """

    ...


class SequentialReflectionAgent:
    """
    A sequential reflection agent that performs research through the order of stages:
    1. Starter - Initial research and analysis
    2. Regression and Analysis - Deep dive into findings
    3. Critical Analysis - Validate and critique findings
    4. Revision - Revise based on critique
    5. Compose Report - Final report composition
    """
    
    def __init__(
        self,
        output: str,
        starter_model: str,
        starter_model_config: dict,
        starter_provider: dict,
        regression_and_analysis_model: str,
        regression_and_analysis_model_config: dict,
        regression_and_analysis_provider: dict,
        regression_and_analysis_tools: list[Callable],
        critical_analysis_model: str,
        critical_analysis_model_config: dict,
        critical_analysis_provider: dict,
        critical_analysis_tools: list[Callable],
        revision_model: str,
        revision_model_config: dict,
        revision_provider: dict,
        revision_tools: list[Callable],
        compose_report_model: str,
        compose_report_model_config: dict,
        compose_report_provider: dict,
    ):
        self.agent_starter = AgentStarter(
            name="agent-starter",
            model=starter_model,
            output_root=output,
            subagents=[
                AgentRegressionAndAnalysis(
                    name="agent-regression-and-analysis",
                    model=regression_and_analysis_model,
                    output_root=output,
                    subagents=[
                        AgentCriticalAnalysis(
                            name="agent-critical-analysis",
                            model=critical_analysis_model,
                            output_root=output,
                            subagents=[
                                AgentRevision(
                                    name="agent-revision",
                                    model=revision_model,
                                    output_root=output,
                                    subagents=[
                                        AgentComposeReport(
                                            name="agent-compose-report",
                                            model=compose_report_model,
                                            output_root=output,
                                            genai_stuff=compose_report_provider,
                                            **compose_report_model_config,
                                        )
                                    ],
                                    tools=revision_tools,
                                    genai_stuff=revision_provider,
                                    **revision_model_config,
                                )
                            ],
                            tools=critical_analysis_tools,
                            genai_stuff=critical_analysis_provider,
                            **critical_analysis_model_config,
                        )
                    ],
                    tools=regression_and_analysis_tools,
                    genai_stuff=regression_and_analysis_provider,
                    **regression_and_analysis_model_config,
                )
            ],
            genai_stuff=starter_provider,
            **starter_model_config,
        )

    def __call__(self, task: str, **kwargs):
        """
        Execute the deep research task.

        Args:
            task: The task to execute.
            **kwargs: Additional keyword arguments to pass to the main agent, it shall update model config in the agent.
        """
        if not task:
            raise ValueError("Text that describes a task is required")

        return self.agent_starter(
            f"""
Your overall task:
{task}

----
What you have to do is **only** break down the overall task into subtasks and transfer them **together as a bundle** to the sibling responsible for regression and analysis.
""",
            **kwargs,
        )
