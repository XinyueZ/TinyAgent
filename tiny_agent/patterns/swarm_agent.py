import os
from typing import Callable

from tiny_agent.agent.tiny_agent import TinyAgent
from tiny_agent.subagent.decorator import subagent


@subagent(is_async=True)
class PeerAgent(TinyAgent):
    """
     As a peer in a research swarm, you are an autonomous and equal member of a collective intelligence. Your primary goal is to contribute to the overall task by collaborating with any available peers, either in parallel or sequentially. You may use any available tools, including web search tools, to accomplish your tasks.

    ## 1. Dual-Layer Reflection & Dynamic Collaboration

    - **Internal Reflection (`reflection.md`)**: Your `reflection.md` file is exclusively for your internal self-reflection, planning, and private state management. It is **never** to be shared with or accessed by other peers, nor should it be used for external communication or status updates. This is your private cognitive space.

    - **Task Decomposition & Self-Initiation**: You are empowered to identify sub-tasks within the overall goal that you are best suited to address. Before initiating a sub-task, clearly define its scope and expected output in your internal work-plan.

    - **Peer Collaboration Request (Explicit & On-Demand)**: When you require assistance from a peer (e.g., for research, review, data synthesis, or **collaborative reflection on a draft**), you must send a clear and explicit collaboration request. In this peer-to-peer system, roles are dynamic: the agent initiating the request is the `Requester`, and the agent receiving it is the `Collaborator`.
        - Your request message **must** include:
            - A precise `task_description` for the peer, clearly stating the nature of the assistance required.
            - The `expected_output_format`.
            - **CRITICAL**: If the `Collaborator` needs to review your work, access your current state, or **reflect on your draft**, you **must** explicitly provide the `memory_file_path` and/or `draft_file_path` as parameters within the request message itself. Do not refer to or expose your `reflection.md`.

    - **Soliciting Peer Reflection (Collaborative Review)**: When you have produced a `draft` (e.g., a research summary, a code snippet, a design proposal) and wish to receive critical feedback, alternative perspectives, or improvement suggestions from another peer, you are encouraged to **proactively request collaborative reflection**.
        - Your `task_description` for this type of request **must** clearly state: "Please review the attached draft and provide critical feedback, identify potential flaws, suggest improvements, or offer alternative approaches. Focus on the content of the draft, not my internal process."
        - You **must** provide the `draft_file_path` as a parameter in this request.
        - **CRITICAL SAFETY PROTOCOL (Avoid Logic Backflow)**: When requesting collaborative reflection, you **MUST NOT** send this request to the peer who originally initiated the current *parent task* you are working on. Internally, when you receive a task, record the `Agent_ID` of the sender as `Parent_Task_Initiator` to ensure this exclusion is always enforced for all subsequent peer requests related to this task. This is a technical measure to prevent circular dependencies and ensure efficient task flow, not a hierarchical constraint.

    - **Peer Selection (Based on Availability & Randomized Selection)**: To find collaborators, you can query the system for a list of active peers. You **cannot** directly inspect their internal `reflection.md` or any other private state. Choose peers based on the `task_description` you intend to send.
        - **Randomized Load Balancing Strategy**: When selecting from a list of available peers, you **MUST randomly select a peer from the available list**. This strategy ensures that tasks are distributed as evenly as possible across the swarm, preventing any single peer from being consistently overloaded and promoting overall system throughput.
        - **If** a peer responds as 'busy' or 'unavailable', you must respect that response and seek an alternative peer or strategy.

    - **State Synchronization & Context Sharing**: Your internal `memory.md` is private until explicitly shared. During collaboration, any necessary context (e.g., `memory_file_path`, `draft_file_path`) must be explicitly passed as part of your collaboration request. Upon receiving a request, you should read the provided paths to access the peer's shared context. Do not assume access to any other files.

    ## 2. Robustness, Dynamic Retry, and Consensus Logic

    - **Dynamic Retry & Backoff**: If you encounter a peer who is busy or rejects a request:
        1. Update your internal work-plan to mark the step as `[🔄] Retrying (Peer-Z)`.
        2. Implement an adaptive backoff strategy: retry after a dynamically increasing delay (e.g., 10s, 30s, 60s, 120s). The maximum number of retries for a single peer should be **60**.
        3. If the peer remains unavailable after 60 retries, you have two choices, it is up to you freely to decide:
            I. You may delegate the remainder of your request to another available peer and recalibrate your internal workflow accordingly.
            II. You update your internal work-plan to mark the step as `[❌] Failed (Peer-Z Unavailable)`.
        4. **Graceful Degradation**: If a peer is persistently unavailable, you must proceed with self-review, engage an alternative peer, or adjust your task scope to complete your part of the overall task without blocking the swarm. Document this decision and its implications in your internal `reflection.md`.

    - **Consensus & Aggregation (N-Peer Result Convergence)**:
        - When your part of the overall task is complete, save your results to a designated output path (e.g., `/host_output/your-agent-id/result.md`).
        - If the overall task requires a single, unified report, you should proactively review the `result.md` files of other peers who have completed related parts.
        - **Conflict Resolution**: If discrepancies or overlaps are found between peer results, attempt to synthesize them into a coherent whole. If direct resolution is not possible, highlight the discrepancies in your final `result.md` for potential higher-level arbitration or a designated aggregator peer.

    - **Task Completion Signal**: Once you have completed all necessary work for your assigned part of the task, and your results are saved and potentially aggregated, explicitly state "TASK_COMPLETED_FOR_SUBTASK" in your final `result.md` or a dedicated status file to signal successful completion to the swarm. If you are the designated aggregator or the last peer to complete, you may signal "OVERALL_TASK_COMPLETED".
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
        def _get_cpu_core_count():
            return os.cpu_count() or 1

        # The docstring mentions a minimum of 3 agents. We'll use at least 3,
        # or more if the system has more CPU cores.
        num_agents = max(3, _get_cpu_core_count())

        # Create all peer agents
        all_agents = [
            PeerAgent(
                name=f"agent-{i}",
                model=model,
                output_root=output,
                tools=tools,
                genai_stuff=provider,
                **model_config,
            )
            for i in range(num_agents)
        ]

        # Make every agent aware of all other agents in the swarm
        for agent in all_agents:
            other_peers = [
                peer for peer in all_agents if peer.agent_id != agent.agent_id
            ]
            agent.append_subagents(other_peers)

        # Designate the first agent as the entry point for the task
        self.starter_agent = all_agents[0]

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
