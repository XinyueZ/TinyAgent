import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tiny_agent.utils.print_utils import format_text

from ..decorator import tool


def _org_result(sub_agent) -> str:
    output_path = f"{sub_agent.output_location}/result.md"
    if Path(output_path).exists():
        return f"The {sub_agent.name} has finished the task and you can check the result file: {str(output_path)}"
    else:
        memory_path = Path(output_path).parent / "memory.md"
        if memory_path.exists():
            return f"The {sub_agent.name} has finished the task without a result file, **but** you can check the memory file: {str(memory_path)}"
        return f"The {sub_agent.name} has finished the task but no result or memory has been generated, please **ignore** this topic research."


@tool()
def transfer_to_subagent(
    from_agent: str,
    to_subagent: str,
    task: str,
) -> str:
    """Transfer a task from an agent to a sub-agent. The agent hand-off the task to the sub-agent.
    **WARNING**: This is the "ONE-TO-ONE" transfer pattern, the sub-agent will execute the task and return the result.

    Args:
        from_agent: Name of an agent, which transfers the task.
        to_subagent: Name of a sub-agent, which receives the task.
        task: The task to transfer.

    Returns:
        A string indicating a path to the result file or memory file. If no result has been generated, a placeholder message will be returned.
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
        "cyan",
    )
    the_subagent = (
        AgentManager().get_agent_by_name(from_agent).get_subagent_by_name(to_subagent)
    )
    if the_subagent is None:
        raise ValueError(
            f"Subagent {to_subagent} not found, please try another possible sub-agent name."
        )
    the_subagent(task)
    return _org_result(the_subagent)


@tool()
def transfer_to_subagents(
    from_agent: str,
    to_subagents: list[str],
    task: str,
) -> dict[str, str]:
    """Transfer the same task to multiple sub-agents in parallel using threads.
    **WARNING**: This is the "ONE-TO-MANY" transfer pattern, all sub-agents will execute the same task concurrently and return their results.
    Only sub-agents marked with `is_async=True` can be used with this tool.

    Args:
        from_agent: Name of an agent, which transfers the task.
        to_subagents: List of sub-agent names, which receive the task.
        task: The task to transfer.

    Returns:
        A dictionary where the key is the sub-agent name and the value is a string indicating a path to the result file or memory file. If no result has been generated, a placeholder message will be returned.
    """
    from tiny_agent.agent.agent_manager import AgentManager

    parent_agent = AgentManager().get_agent_by_name(from_agent)
    the_subagents = []
    for name in to_subagents:
        sa = parent_agent.get_subagent_by_name(name)
        if sa is None:
            raise ValueError(
                f"Subagent '{name}' not found, please try another possible sub-agent name."
            )
        if not getattr(sa, "_is_async", False):
            raise ValueError(
                f"Subagent '{name}' is not async (is_async=True). "
                f"Only async sub-agents can be used with transfer_to_subagents."
            )
        the_subagents.append((name, sa))

    format_text(
        f"""
- From Agent: {from_agent}
- To Subagents: {', '.join(to_subagents)}
- Task:
{task}
""",
        "Transfer to Subagents (parallel)",
        "cyan",
    )

    max_workers = min(len(the_subagents), os.cpu_count() or 1)
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_name = {executor.submit(sa, task): name for name, sa in the_subagents}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = f"Error from subagent '{name}': {e}"

    for name in list(results.keys()):
        sa = parent_agent.get_subagent_by_name(name)
        results[name] = _org_result(sa)
    return results
