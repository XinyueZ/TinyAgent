from __future__ import annotations

from typing import Callable


from ..tools.coding.coding_tool import run_python_code
from .tiny_agent import (
    GenaiStuffDict,
    OllamaStuffDict,
    TinyAgent,
)


CODING_AGENT_INSTRUCTION = """
You are an expert assistant who can solve any task using code blobs. You will be given a task to solve as best you can.
To do so, you have been given access to a list of tools: these tools are basically Python functions which you can call with code.

<coding-tools>
You have the following code execution tools available:
{run_code_tools}
</coding-tools>

<preferred-libraries>
When writing code, prefer these libraries for optimal performance:
{perf_libs}
</preferred-libraries>

<preferred-functions>
Here are pre-written tool functions you can copy, edit and reuse directly in your code (ensure you import appropriate dependencies):
{coding_tools}
</preferred-functions>

<task>
This is where the user-defined task you need to complete is specified:
{task}
</task>

Summary:
You use coding-tools to run code.
**Always** reuse functions from preferred-functions to assist you in completing the code.
**Think about** how to integrate the preferred-functions into your code.
You need to install necessary dependencies and libraries yourself.
The libraries in preferred-libraries are recommended for performance optimization.
"""


class TinyCodingAgent(TinyAgent):
    run_code_tools = [run_python_code]

    def __init__(
        self,
        perf_libs: list[str] | None = None,
        coding_tools: list[Callable] | None = None,
        **kwargs,
    ):
        self.perf_libs = perf_libs or []
        self.coding_tools = coding_tools or []
        super().__init__(**kwargs)

    def wrap_contents(self, contents: str) -> str:
        run_code_tools_str = "\n".join(
            [
                t.__name__ if hasattr(t, "__name__") else str(t)
                for t in self.run_code_tools
            ]
        )
        coding_agent_instruction_contents = CODING_AGENT_INSTRUCTION.format(
            perf_libs=", ".join(self.perf_libs),
            run_code_tools=run_code_tools_str,
            coding_tools="\n\n".join([str(t) for t in self.coding_tools]),
            task=contents,
        )
        return coding_agent_instruction_contents

    def get_buildin_tools(self) -> list[Callable]:
        return super().get_buildin_tools() + self.run_code_tools
