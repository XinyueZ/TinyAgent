from pathlib import Path
from ...utils.print_utils import format_text
from ..decorator import *


@tool()
def list_dir(target_dir: str, is_absolute: bool = True) -> str:
    """Recursively list all files and directories under the target directory.

    Args:
        target_dir: The target directory to list.
        is_absolute: If True, return absolute paths; otherwise, return relative paths to target_dir.

    Returns:
        A Python `str` containing a list of all file and directory paths.
    """
    try:
        target_path = Path(target_dir).resolve()
        if not target_path.exists():
            return f"Directory not found: {target_dir}"
        if not target_path.is_dir():
            return f"Not a directory: {target_dir}"

        all_paths = []
        for item in target_path.rglob("*"):
            if is_absolute:
                all_paths.append(str(item.resolve()))
            else:
                all_paths.append(str(item.relative_to(target_path)))

        result = "\n".join(all_paths)
        format_text(result, f"List Dir: {target_dir}", "green")
        return result if result else "Directory is empty."
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"Failed to list directory. Error: {str(e)}"


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
