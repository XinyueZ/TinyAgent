from pathlib import Path
from ..utils.print_utils import format_text
from datetime import datetime, timezone
from .decorator import *


@tool()
def get_current_datetime_in_utc() -> str:
    """Get current datetime in UTC, it is NOW

    Return:
        in string format: the current datetime in UTC
    """

    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return current_time


@tool()
def get_current_datetime_in_local() -> str:
    """Get current datetime in local timezone, it is NOW

    Return:
        in string format: the current datetime in local timezone
    """

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return current_time


@tool()
def read_file(file_full_path: str) -> str:
    """Read content from a file of local filesystem.

    Args:
        file_full_path: The full path to the file to read.

    Returns:
        A Python `str` with the file content or error message.
    """
    try:
        with open(file_full_path, "r") as f:
            content = f.read()
            format_text(content, f"Read File: {file_full_path}", "green")
        return content
    except FileNotFoundError:
        return f"File not found: {file_full_path}"
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to read file. Error: {str(e)}"


@tool()
def write_file(text: str, file_full_path: str) -> str:
    """Write text content to a file, creating directories if needed.
    Use this tool if you want to save information to the local filesystem.

    Args:
        text: The text content to write to the file.
        file_full_path: The full path to the file to be written.

    Returns:
        A Python `str` with confirmation that the file was written.
    """
    try:
        Path(file_full_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_full_path, "w") as f:
            f.write(text)
            format_text(text, f"Write File: {file_full_path}", "green")
        return f"File written successfully: {file_full_path}"
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to write file. Error: {str(e)}"


@tool()
def append_to_file(text: str, file_full_path: str) -> str:
    """Append text content to a file, creating directories if needed.
    Use this tool if you want to append information to the local filesystem.

    Args:
        text: The text content to append to the file.
        file_full_path: The full path to the file to append to.

    Returns:
        A Python `str` with confirmation that the content was appended.
    """
    try:
        Path(file_full_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_full_path, "a") as f:
            f.write(text)
            format_text(text, f"Append to File: {file_full_path}", "green")
        return f"Content appended successfully to: {file_full_path}"
    except FileNotFoundError:
        return f"File not found: {file_full_path}"
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to append to file. Error: {str(e)}"


@tool()
def file_exists(file_full_path: str) -> str:
    """Check if a file exists at the given path in the local filesystem.

    Args:
        file_full_path: The full path to the file to check.

    Returns:
        A Python `str` indicating whether the file exists.
    """
    try:
        exists = Path(file_full_path).exists()
        result = f"File {'exists' if exists else 'does not exist'}: {file_full_path}"
        format_text(result, "File Exists Check", "blue")
        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to check file existence. Error: {str(e)}"


@tool()
def read_work_plan() -> str:
    """Read the work-plan from the file.

    Returns:
        A Python `str` containing the work-plan content.
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    try:
        with open(f"{agent_output_location}/work_plan.md", "r") as f:
            work_plan = f.read()
            format_text(work_plan, "Read Work-plan", "green")
        return work_plan
    except FileNotFoundError:
        import traceback

        traceback.print_exc()
        return "**No work-plan has been created yet."


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
    try:
        Path(agent_output_location).mkdir(parents=True, exist_ok=True)
        with open(f"{agent_output_location}/work_plan.md", "w") as f:
            f.write(work_plan)
            format_text(work_plan, "Create Work-plan", "red")
        return f"""Work-plan created in file: {agent_output_location}/work_plan.md
-----
#### Work-plan
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
    try:
        with open(f"{agent_output_location}/work_plan.md", "w") as f:
            f.write(updated_work_plan)
            format_text(updated_work_plan, "Update Work-plan", "red")
        return f"Updated work-plan: {updated_work_plan}"
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
    try:
        Path(agent_output_location).mkdir(parents=True, exist_ok=True)
        with open(f"{agent_output_location}/reflection.md", "a") as f:
            f.write(reflection)
            f.write("\n")
            format_text(reflection, "Reflect", "red")
        return f"**Reflection recorded:**\n {reflection}\n"
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
    try:
        with open(f"{agent_output_location}/memory.md", "r") as f:
            memory = f.read()
            format_text(memory, "Read memory", "green")
        return memory
    except FileNotFoundError:
        format_text("No memory has been created yet.", "Read memory", "yellow")
        return "No memory has been created yet."
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to read memory. Error: {str(e)}"


@tool()
def update_memory(entry: str) -> str:
    """Append a new entry to the memory file to track execution progress.

    Args:
        entry: The new entry to append to the memory file.

    Returns:
        A Python `str` confirming that the memory entry was added.
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    try:
        Path(agent_output_location).mkdir(parents=True, exist_ok=True)
        with open(f"{agent_output_location}/memory.md", "a") as f:
            f.write(entry)
            f.write("\n")
            format_text(entry, "Update memory", "red")
        return f"A new memory entry added: {entry}"
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to update memory. Error: {str(e)}"
