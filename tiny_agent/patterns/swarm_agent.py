from typing import Callable

from tiny_agent.agent.tiny_agent import TinyAgent
from tiny_agent.subagent.decorator import subagent


@subagent(is_async=True)
class PeerAgent(TinyAgent):
    """
    As a peer in a research team, you can collaborate with your peers either in parallel or one at a time to complete tasks.
    You may use any available tools, including web search tools, to accomplish your tasks.

    **Flexible Working Style**
    - When requesting help from peers, follow these guidelines:
        - If you have a single task requiring one peer's assistance, consider requesting one peer to collaborate.
        - If you have multiple tasks requiring simultaneous assistance from multiple peers, consider requesting them to collaborate in parallel.
    - **IMPORTANT**: When executing tasks, prioritize conciseness and efficiency over verbosity and perfectionism.
    - **Before** delivering your final response to the requester, you can engage **any available** peers to help refine and improve your findings. Provide a detailed introduction of your work and ideas, and submit them to an **available** peer.
    - **IMPORTANT**: When seeking assistance from peers, you must exclude the peer who assigned the current task to you or made the current request.
    - During collaboration, you must share the storage path to your memory file or your results file.

    Once you have completed all necessary work, store your final results with the following content:

    Please provide:
    - **Topic**: The name of each research topic
    - **Key Findings**: A summary of the main findings for each topic
    - **Description**: A brief synthesis of insights across all researched topics
    - **Citations Including URLs**: All referenced sources, organized by topic
    - (Optional) **Cross-Topic Insights**: Any patterns or connections observed across multiple topics
    """

    ...


class SwarmAgent:
    """
    A swarm of agents consisting of 3 agents (currently set as the minimum combination) that collaborate with each other to complete tasks.
    Full freedom to perform until the task is completed.
    """

    def __init__(
        self,
        output: str,
        model: str,
        model_config: dict,
        provider: dict,
        tools: list[Callable],
    ):

        b = PeerAgent(
            name="agent-b",
            model=model,
            output_root=output,
            tools=tools,
            genai_stuff=provider,
            **model_config,
        )

        c = PeerAgent(
            name="agent-c",
            model=model,
            output_root=output,
            tools=tools,
            genai_stuff=provider,
            **model_config,
        )

        self.starter_agent = a = PeerAgent(
            name="agent-a",
            model=model,
            output_root=output,
            tools=tools,
            subagents=[b, c],
            genai_stuff=provider,
            **model_config,
        )

        b.append_subagents([a, c])
        c.append_subagents([a, b])

    def __call__(self, task: str, **kwargs):
        """
        Execute the deep research task.

        Args:
            task: The task to execute.
            **kwargs: Additional keyword arguments to pass to the main agent, it shall update model config in the agent.
        """
        if not task:
            raise ValueError("Text that describes a task is required")

        return self.starter_agent(
            f"""
Your overall task:
{task}
""",
            **kwargs,
        )
