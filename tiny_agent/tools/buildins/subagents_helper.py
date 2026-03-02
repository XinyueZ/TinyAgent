import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tiny_agent.agent.agent_manager import AgentManager
from tiny_agent.utils.print_utils import format_text

from ..decorator import tool

_locks_guard = threading.Lock()
_transfer_to_subagent_locks: dict[str, threading.Lock] = {}
_transfer_to_subagents_locks: dict[str, threading.Lock] = {}


def _get_lock(lock_map: dict[str, threading.Lock], agent_id: str) -> threading.Lock:
    with _locks_guard:
        lock = lock_map.get(agent_id)
        if lock is None:
            lock = threading.Lock()
            lock_map[agent_id] = lock
        return lock


def _org_result(sub_agent) -> str:
    output_path = f"{sub_agent.output_location}/result.md"
    if Path(output_path).exists():
        return f"The {sub_agent.name} has finished the task and you can check the result file: {str(output_path)}"
    else:
        memory_path = f"{sub_agent.output_location}/memory.md"
        if Path(memory_path).exists():
            return f"The {sub_agent.name} has finished the task without a result file, **but** you can check the memory file: {str(memory_path)}"
        return f"The {sub_agent.name} has finished the task but no result or memory has been generated, please **ignore** this topic research."


def _record_transfer_history(parent_agent, task: str):
    transfer_history_path = f"{parent_agent.output_location}/agent_transfer_history.md"
    with open(transfer_history_path, "a") as f:
        f.write(f"\n{task}\n")


@tool()
def transfer_to_subagent(
    from_agent: str,
    to_subagent: str,
    task: str,
) -> str:
    """Transfer a task from an agent to a sub-agent. The agent hand-off the task to the sub-agent.
    **WARNING**: This is the "ONE-TO-ONE" transfer pattern, the sub-agent will execute the task and return the result.
    **IMPORTANT**: Only sub-agents setup with `is_async=False` can be used with this tool.

    Args:
        from_agent: Name of an agent, which transfers the task.
        to_subagent: Name of a sub-agent, which receives the task.
        task: The task to transfer.

    Returns:
        A string indicating a path to the result file or memory file. If no result has been generated, a placeholder message will be returned.
    """
    parent_agent = AgentManager().get_agent_by_name(from_agent)
    lock = _get_lock(_transfer_to_subagent_locks, parent_agent.agent_id)
    if not lock.acquire(blocking=False):
        return "transfer_to_subagent is busy for this parent agent (another transfer_to_subagent call is in progress); skipped"

    try:
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
        sa = parent_agent.get_subagent_by_name(to_subagent)
        if sa is None:
            raise ValueError(
                f"Subagent {to_subagent} not found, please try another possible sub-agent name, from agent: {from_agent}"
            )
        # Check if it's a valid sync subagent
        if not sa.is_subagent:
            raise ValueError(
                f"{to_subagent} is not a sub-agent. "
                f"Only sub-agents can be used with transfer_to_subagent, from agent: {from_agent}"
            )
        if getattr(sa, "_is_async", False):
            raise ValueError(
                f"Subagent {to_subagent} has is_async=True. "
                f"Cannot use async sub-agents with transfer_to_subagent (use transfer_to_subagents instead), from agent: {from_agent}"
            )
        if sa.is_busy:
            return f"Subagent (name: {sa.name}, id: {sa.agent_id}) is currently busy processing another task; concurrent calls are not allowed. Please try again later or use another sub-agent, from agent: {from_agent}"

        _record_transfer_history(parent_agent, task)
        sa(task)
        return _org_result(sa)
    finally:
        lock.release()


@tool()
def transfer_to_subagents(
    from_agent: str,
    to_subagents: list[str],
    tasks: list[str],
) -> dict[str, str]:
    """Transfer the same task to multiple sub-agents in parallel using threads.
    **WARNING**: This is the "ONE-TO-MANY" transfer pattern, all sub-agents will execute the same task concurrently and return their results.
    **IMPORTANT**: Only sub-agents setup with `is_async=True` can be used with this tool.

    Args:
        from_agent: Name of an agent, which transfers the task.
        to_subagents: List of sub-agent names, which receive the task.
        tasks: The tasks that will be transferred. The order to the list corresponds to the order of sub-agents in `to_subagents`. If the list is shorter than `to_subagents`, the last task in the list will be used for the remaining sub-agents.

    Returns:
        A dictionary where the key is the sub-agent name and the value is a string indicating a path to the result file or memory file. If no result has been generated, a placeholder message will be returned.
    """
    parent_agent = AgentManager().get_agent_by_name(from_agent)
    lock = _get_lock(_transfer_to_subagents_locks, parent_agent.agent_id)
    if not lock.acquire(blocking=False):
        return {
            "__busy__": "transfer_to_subagents is busy for this parent agent (another transfer_to_subagents call is in progress); skipped"
        }

    try:
        the_subagents = []
        for name in to_subagents:
            sa = parent_agent.get_subagent_by_name(name)
            if sa is None:
                raise ValueError(
                    f"Subagent '{name}' not found, please try another possible sub-agent name."
                )
            # Check if it's a valid async subagent
            if not sa.is_subagent:
                raise ValueError(
                    f"'{name}' is not a sub-agent. "
                    f"Only sub-agents can be used with transfer_to_subagents."
                )
            if not getattr(sa, "_is_async", False):
                raise ValueError(
                    f"Subagent '{name}' has is_async=False. "
                    f"Only async sub-agents (is_async=True) can be used with transfer_to_subagents for parallel execution."
                )
            if not sa.is_busy:
                the_subagents.append((name, sa))

        if len(tasks) == 0:
            return {"ERROR": "No tasks provided. Please provide at least one task."}

        if len(the_subagents) == 0:
            busy_agents = ", ".join(to_subagents)
            return {
                "WARNING": f"All requested subagents are busy: {busy_agents}. Please try again later or use different subagents or approaches."
            }

        format_text(
            f"""
- From Agent: {from_agent}
- To Subagents: {', '.join(to_subagents)}
- Tasks:
{tasks}
""",
            "Transfer to Subagents (parallel)",
            "cyan",
        )

        # Distribute tasks evenly across available subagents
        if len(tasks) <= len(the_subagents):
            # Original behavior: repeat last task if we have more agents than tasks
            distributed_tasks = tasks + [tasks[-1]] * (len(the_subagents) - len(tasks))
        else:
            # New behavior: merge tasks evenly when we have more tasks than agents
            distributed_tasks = []
            tasks_per_agent = len(tasks) // len(the_subagents)
            remainder = len(tasks) % len(the_subagents)

            start_idx = 0
            for i in range(len(the_subagents)):
                # First 'remainder' agents get one extra task
                count = tasks_per_agent + (1 if i < remainder else 0)
                agent_tasks = tasks[start_idx : start_idx + count]
                # Merge multiple tasks into one with separator
                merged_task = "\n\n---\n\n".join(agent_tasks)
                distributed_tasks.append(merged_task)
                start_idx += count

        max_workers = min(len(the_subagents), os.cpu_count() or 1)
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_name = {
                executor.submit(sa, task): name
                for (name, sa), task in zip(the_subagents, distributed_tasks)
            }
            _record_transfer_history(parent_agent, tasks)
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    furture_result = future.result()
                    results[name] = furture_result
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    results[name] = f"Error from subagent '{name}': {e}"

        for name in list(results.keys()):
            sa = parent_agent.get_subagent_by_name(name)
            results[name] = _org_result(sa)
        return results
    finally:
        lock.release()
