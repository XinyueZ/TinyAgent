from pathlib import Path

from ...utils.print_utils import format_text
from ..decorator import *


@tool()
def read_work_plan() -> str:
    """Read the work-plan from the file.

    Returns:
        A Python `str` containing the work-plan content.
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    agent_name = ctx["agent_info"]["agent_name"]
    agent_id = ctx["agent_info"]["agent_id"]
    try:
        file_location = f"{agent_output_location}/work_plan.md"
        with open(file_location, "r") as f:
            work_plan = f.read()
            format_text(
                work_plan,
                f"{agent_name}-{agent_id} | Read Work-plan | {file_location}",
                "green",
            )
        return f"""Work-plan (saved in file:{file_location}):
{work_plan}
"""
    except FileNotFoundError:
        format_text(
            "**No work-plan has been created yet.",
            f"{agent_name}-{agent_id} | Read Work-plan | {file_location}",
            "yellow",
        )
        return "**No work-plan has been created yet."
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to read work-plan. Error: {str(e)}"


@tool()
def create_work_plan(work_plan: str) -> str:
    """Create the work-plan.

    Args:
        work_plan: The work-plan content to be created.

    Returns:
        A Python `str` confirming that the work-plan was created.
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    agent_name = ctx["agent_info"]["agent_name"]
    agent_id = ctx["agent_info"]["agent_id"]
    try:
        file_location = str(
            (p := Path(agent_output_location)).mkdir(parents=True, exist_ok=True)
            or p / "work_plan.md"
        )
        with open(file_location, "w") as f:
            f.write(work_plan)
            format_text(
                work_plan,
                f"{agent_name}-{agent_id} | Create Work-plan | {file_location}",
                "red",
            )
        return f"""Work-plan created (saved in file: {file_location}):
{work_plan}
"""
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to create work plan. Error: {str(e)}"


@tool()
def update_work_plan(updated_work_plan: str) -> str:
    """Update the work-plan.

    Args:
        updated_work_plan: The updated work-plan content.

    Returns:
        A Python `str` confirming that the work-plan was updated.
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    agent_name = ctx["agent_info"]["agent_name"]
    agent_id = ctx["agent_info"]["agent_id"]
    try:
        file_location = str(
            (p := Path(agent_output_location)).mkdir(parents=True, exist_ok=True)
            or p / "work_plan.md"
        )
        with open(file_location, "w") as f:
            f.write(updated_work_plan)
            format_text(
                updated_work_plan,
                f"{agent_name}-{agent_id} | Update Work-plan | {file_location}",
                "red",
            )
        return f"""Updated work-plan(saved in file: {file_location}):
{updated_work_plan}"""
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to update work-plan. Error: {str(e)}"


@tool()
def reflect(reflection: str) -> str:
    """Perform reflection for decision-making.

    Args:
        reflection: Your detailed reflection content.

    Returns:
        A Python `str` confirming that the reflection was recorded for decision-making.
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    agent_name = ctx["agent_info"]["agent_name"]
    agent_id = ctx["agent_info"]["agent_id"]
    try:
        file_location = str(
            (p := Path(agent_output_location)).mkdir(parents=True, exist_ok=True)
            or p / "reflection.md"
        )
        with open(file_location, "a") as f:
            f.write(reflection)
            f.write("\n")
            format_text(
                reflection,
                f"{agent_name}-{agent_id} | Reflect | {file_location}",
                "red",
            )
        return f"""Reflection recorded(file: {file_location}):
{reflection}"""
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to save reflection. Error: {str(e)}"


@tool()
def read_memory() -> str:
    """Read the memory file to review accumulated execution context.

    Returns:
        A Python `str` containing the memory content.
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    agent_name = ctx["agent_info"]["agent_name"]
    agent_id = ctx["agent_info"]["agent_id"]
    try:
        file_location = f"{agent_output_location}/memory.md"
        with open(file_location, "r") as f:
            memory = f.read()
            format_text(
                memory,
                f"{agent_name}-{agent_id} | Read memory | {file_location}",
                "green",
            )
        return f"""Memory (saved in file: {file_location}):
{memory}"""
    except FileNotFoundError:
        format_text(
            "No memory has been created yet.",
            f"{agent_name}-{agent_id} | Read memory | {file_location}",
            "yellow",
        )
        return "No memory has been created yet."
    except Exception as e:
        return f"Failed to read memory. Error: {str(e)}"


@tool()
def update_memory(entry: str) -> str:
    """Append a new entry to the memory file to track execution progress.

    Args:
        entry: The new entry to append to the memory file.

    Returns:
        A Python `str` confirming that the memory entry was appended.
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    agent_name = ctx["agent_info"]["agent_name"]
    agent_id = ctx["agent_info"]["agent_id"]
    try:
        file_location = str(
            (p := Path(agent_output_location)).mkdir(parents=True, exist_ok=True)
            or p / "memory.md"
        )
        with open(file_location, "a") as f:
            f.write(entry)
            f.write("\n")
            format_text(
                entry,
                f"{agent_name}-{agent_id} | Update memory | {file_location}",
                "red",
            )
        return f"""New memory entry appended (saved in file: {file_location}):
{entry}"""
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to update memory. Error: {str(e)}"
