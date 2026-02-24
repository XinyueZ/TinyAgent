import inspect
import os
from contextvars import ContextVar
from functools import wraps
from typing import Callable, Optional

from ..utils.print_utils import format_text

# Context variable for implicit context passing to decorated functions
_tool_context: ContextVar[dict] = ContextVar("tool_context", default={})

# Context variable for agent info, set by TinyAgent before calling tools
# This is thread-safe and avoids race conditions in concurrent execution
_agent_info_context: ContextVar[dict] = ContextVar("agent_info_context", default=None)


def get_tool_context() -> dict:
    """Get the implicit context dict passed by the @tool() decorator.

    This can be called inside any function decorated with @tool() to access:
    - caller_info: Information about who called this function
    - agent_info: Information about the TinyAgent using this tool
    - func_name: Name of the decorated function

    Example:
        @tool()
        def greet():
            ctx = get_tool_context()
            print(f"Called by: {ctx['caller_info']['caller_function']}")
            return "hello"
    """
    return _tool_context.get()


def default_tool_extra_fun(
    func_name_to_decorate: str, caller_info: dict, agent_info: dict
) -> str:
    """Get the interaction history, including full memory and work-plan.

    Args:
        func_name_to_decorate: The name of the function being decorated
        caller_info: Information about who called this function
        agent_info: Information about the TinyAgent using this tool

    Returns:
        A Python `str` with the following format:
        1. response: The full persistent interactions
        2. status: The status of the tool execution and reason
    """
    ctx = get_tool_context()
    agent_output_location = ctx["agent_info"]["output_location"]
    work_plan = ""
    try:
        with open(f"{agent_output_location}/work_plan.md", "r") as f:
            work_plan = f.read()
    except FileNotFoundError:
        pass

    memory = ""
    try:
        with open(f"{agent_output_location}/memory.md", "r") as f:
            memory = f.read()
    except FileNotFoundError:
        pass

    format_str = f"""
{"## Work-plan" if len(work_plan) > 0 else ""}
{work_plan or ""}

{"## Memory" if len(memory) > 0 else ""}
{memory or ""} 

> caller_info: {caller_info}
> agent_info: {agent_info}
""".strip()
    if int(os.getenv("VERBOSE", "0")) > 1:
        format_text(
            format_str,
            "[Agent] {agent} | [Tool] {func_name_to_decorate} | Interactions".format(
                agent=agent_info["agent_name"],
                func_name_to_decorate=func_name_to_decorate,
            ),
            "blue",
        )
    return format_str


DEFAULT_TOOL_EXTRA_PROMPT = """
**Response from this tool:**
{result} 

**Information about the agent using this tool:**
{agent_info}

**Information about the mechanism calling this tool:**
{caller_info}

**Here are all the interaction records (aka. the conversation history, memory, i.e., past information) so far; continue to work based on these records:**

- Work-plan: Record of the work-plan and the status of each step
- Memory: Record of the memory of the entire interaction **history** so far 

Here are the interaction records so far:
{extra}
"""


def tool(
    extra_fn: Callable = default_tool_extra_fun,
    extra_fn_prompt: str = DEFAULT_TOOL_EXTRA_PROMPT,
):
    """Decorator that automatically appends interaction history to tool return values.

    Thread safety:
        This decorator is thread-safe for concurrent multi-agent execution.
        - All mutable state (agent_info, caller_info, context) is stored in ContextVar,
          which provides per-thread isolation automatically.
        - The wrapper._agent_info attribute is a shared fallback only; at runtime,
          TinyAgent._create_tool_copy sets _agent_info_context via ContextVar before
          each call, so the shared attribute is never read in concurrent scenarios.
        - No threading.Lock is used, because different agents calling the same tool
          concurrently operate on isolated file paths (different output_location),
          so there is no shared resource contention.

    Args:
        extra_fn: A function that takes a string argument (the name of the function to decorate).

    Returns:
        A decorator function that wraps the original function.

    Example:
        @tool()
        def greet():
            return "hello"

        greet()  # Returns "hello" + interaction history
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get caller information (stack frame is thread-local, safe without lock)
            caller_frame = inspect.currentframe().f_back
            caller_info = {
                "caller_filename": caller_frame.f_code.co_filename,
                "caller_lineno": caller_frame.f_lineno,
                "caller_function": caller_frame.f_code.co_name,
            }

            # Get agent info from ContextVar (thread-safe) or fall back to wrapper attribute
            agent_info = _agent_info_context.get() or getattr(
                wrapper, "_agent_info", None
            )

            # Set implicit context for the decorated function via ContextVar (thread-safe)
            context = {
                "caller_info": caller_info,
                "agent_info": agent_info,
                "func_name": func.__name__,
            }
            token = _tool_context.set(context)
            try:
                result = func(*args, **kwargs)
                extra = extra_fn(func.__name__, caller_info, agent_info)
            finally:
                _tool_context.reset(token)

            raw_response = extra_fn_prompt.format(
                result=result,
                agent_info=agent_info,
                caller_info=caller_info,
                extra=extra,
            )
            if int(os.getenv("VERBOSE", "0")) > 1:
                format_text(
                    raw_response,
                    f"⌭ [Agent] {agent_info.get('agent_name', 'unknown')} | [Tool] {func.__name__} | Raw response",
                    "cyan",
                )
            return {
                "tool_response": result,
                "extra": extra,
                "caller_info": caller_info,
                "agent_info": agent_info,
                "raw_response": raw_response,
            }

        # Initialize agent info attribute
        wrapper._agent_info = None

        return wrapper

    return decorator


class _CodingToolCallable:
    def __init__(self, tool_func: Callable, original_func: Callable):
        self._tool_func = tool_func
        self._original_func = original_func

        self.__wrapped__ = getattr(tool_func, "__wrapped__", original_func)
        self.__name__ = getattr(
            tool_func, "__name__", getattr(original_func, "__name__", "")
        )
        self._agent_info = getattr(tool_func, "_agent_info", None)

    def __call__(self, *args, **kwargs):
        return self._tool_func(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._tool_func, name)

    def __str__(self) -> str:
        func = self._original_func
        try:
            source = inspect.getsource(func)
        except Exception:
            source = repr(func)

        lines = source.splitlines()
        i = 0
        while i < len(lines):
            stripped = lines[i].lstrip()
            if stripped.startswith("@"):  # decorator line
                i += 1
                continue
            if stripped == "":
                i += 1
                continue
            break

        return "\n".join(lines[i:]).rstrip()


def coding_tool(
    extra_fn: Callable = default_tool_extra_fun,
    extra_fn_prompt: str = DEFAULT_TOOL_EXTRA_PROMPT,
):
    """Like @tool(), but `str(tool_func)` prints full source.

    Can be stacked with @tool(). Recommended order:
        @coding_tool()
        @tool()
        def f(...):
            ...

    (If @tool() is the outer decorator, the resulting object is a plain function wrapper,
    and Python's `str()` will not use instance-level overrides.)

    Example:
        @coding_tool()
        def add(a: int, b: int) -> int:
            return a + b

        print(str(add))
        # -> "def add(a: int, b: int) -> int:\n    return a + b\n"
    """

    def decorator(func: Callable):
        if isinstance(func, _CodingToolCallable):
            return func

        original = inspect.unwrap(func)

        if hasattr(func, "_agent_info"):
            return _CodingToolCallable(func, original)

        wrapped = tool(extra_fn=extra_fn, extra_fn_prompt=extra_fn_prompt)(func)
        return _CodingToolCallable(wrapped, original)

    return decorator
