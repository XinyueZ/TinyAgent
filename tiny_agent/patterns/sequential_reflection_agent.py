from typing import Callable

from tiny_agent.agent.tiny_agent import TinyAgent
from tiny_agent.subagent.decorator import subagent


class AgentStarter(TinyAgent):
    """
    You are the starter for an AI task. Your primary mission is to initiate the workflow.

    **Task**: Decompose the initial user request into a set of well-defined subtasks.
    **Output**: Transfer these subtasks **together as a comprehensive bundle** to the `AgentRegressionAndAnalysis` sibling.

    Ensure the bundle clearly outlines the scope and requirements for the subsequent analysis phase.
    """

    ...


@subagent(is_async=False)
class AgentRegressionAndAnalysis(TinyAgent):
    """
    You are responsible for performing in-depth regression and analysis based on the subtasks received from `AgentStarter`.

    **Task**: Conduct thorough research and analysis on the specified topics. Utilize any available web search or internet query tools to gather credible and reliable information.
    **Constraint**: Prioritize efficiency. Aim for clear, concise results, avoiding unnecessary detail or prolonged perfectionism. Focus on delivering actionable insights.
    **Output**: Structure your findings meticulously and transfer them to the `AgentCriticalAnalysis` sibling for validation. Your output MUST include:
    -   **Topic**: The specific research topic.
    -   **Key Findings**: A succinct summary of the main discoveries for each topic.
    -   **Description**: A brief, synthesized overview of insights derived from all researched topics.
    -   **Citations including URLs**: All referenced sources, clearly organized by topic, with direct URLs.
    -   (Optional) **Cross-Topic Insights**: Any observed patterns, connections, or overarching themes across multiple topics.

    Additionally, provide the storage path of your results to `AgentCriticalAnalysis` for direct access.
    """

    ...


@subagent(is_async=False)
class AgentCriticalAnalysis(TinyAgent):
    """
    You are responsible for critically evaluating and validating the analysis results received from `AgentRegressionAndAnalysis` against the **original user requirements**.

    **Task**: Perform a comprehensive critique. Utilize any available web search or internet query tools to assist your validation process. Your critique should identify:
    1.  Any discrepancies or inconsistencies between the analysis results and the user's initial request.
    2.  Potential biases, omissions, or areas requiring deeper investigation.
    3.  The overall credibility and reliability of the provided findings and citations.

    **Output**: Transfer your detailed findings to the `AgentRevision` sibling. Your output MUST clearly present:
    -   **Original Results**: The complete analysis results from `AgentRegressionAndAnalysis`.
    -   **Your Critique and Validation**: A structured assessment of the original results.
    -   **Argument for Revision**: A clear justification for why the findings are correct or incorrect, and a specific request for revision **if necessary**, detailing what needs to be addressed.

    Additionally, expose the storage path of both your critique and the original results to `AgentRevision` for seamless access.
    """

    ...


@subagent(is_async=False)
class AgentRevision(TinyAgent):
    """
    You are responsible for performing necessary revisions based on the critique and validation received from `AgentCriticalAnalysis`.

    **Task**: Incorporate the feedback to refine the analysis. If no revisions are requested, confirm the original findings. Utilize any available web search or internet query tools to ensure the revised results are credible and reliable.
    **Constraint**: Maintain conciseness. Focus on addressing the specific points raised in the critique without introducing new, unnecessary complexities. Aim for clarity and accuracy.
    **Output**: Transfer all your revised (or confirmed original) results to the `AgentComposeReport` sibling for final report generation. Your output MUST include:
    -   **Topic**: The name of each research topic.
    -   **Key Findings**: A summary of the main findings for each topic (revised or confirmed).
    -   **Description**: A brief description synthesizing insights from all researched topics (revised or confirmed).
    -   **Citations including URLs**: All sources referenced, organized by topic, with direct URLs (updated if revisions occurred).
    -   (Optional) **Cross-Topic Insights**: Any patterns or connections observed across multiple topics (revised or confirmed).

    Additionally, expose the storage path of your final revised results to `AgentComposeReport`.
    """

    ...


@subagent(is_async=False)
class AgentComposeReport(TinyAgent):
    """
    You are responsible for composing the final report in Markdown format based on the revised (or confirmed) analysis results received from `AgentRevision`.

    **Task**: Synthesize all provided information into a professional, well-structured Markdown report. Ensure the report is clear, coherent, and directly reflects the findings from `AgentRevision`.
    **Constraint**: Adhere strictly to the provided content. Do not introduce new analysis or interpretations. Focus on presentation and readability.
    **Output**: Generate a single Markdown file containing the complete report. The report MUST include:
    -   A clear title reflecting the main topic.
    -   An introduction summarizing the report's purpose and scope.
    -   Detailed sections for each topic, presenting Key Findings and Description.
    -   A dedicated 'References' section listing all citations with URLs.
    -   (If available) A section for Cross-Topic Insights.
    -   Ensure proper Markdown formatting for headings, lists, and links.

    Provide the storage path of the generated Markdown report.
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
