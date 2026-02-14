from tiny_agent.utils.print_utils import format_text

from ..decorator import tool


@tool()
def transfer_to_subagent(
    from_agent: str,
    to_subagent: str,
    task: str,
):
    """Transfer a task from an agent to a sub-agent. The agent hand-off the task to the sub-agent.

    Args:
        from_agent: Name of an agent, which transfers the task.
        to_subagent: Name of a sub-agent, which receives the task.
        task: The task to transfer.
    """
    from tiny_agent.agent.agent_manager import AgentManager

    format_text(
        f"""
- From Agent: {from_agent}
- To Subagent: {to_subagent}
- Task: 
{task}
""",
        f"Transfer to Subagent",
        "green",
    )
    the_subagent = (
        AgentManager().get_agent_by_name(from_agent).get_subagent_by_name(to_subagent)
    )
    if the_subagent is None:
        raise ValueError(
            f"Subagent {to_subagent} not found, please try another possible sub-agent name."
        )
    res = the_subagent(task)
    return res
