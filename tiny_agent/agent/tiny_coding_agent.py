from __future__ import annotations

from typing import Any, Callable
from ..tools.coding.run_code import run_python_file
from .tiny_agent import TinyAgent
import os

CODING_AGENT_INSTRUCTION = """
<additional-instruction>
You are an expert who can solve user tasks efficiently writing code and using code. 
Your goal is to fulfill the user's requirements as best as possible.

<coding-tools>
Below are **pre-written Python functions** (coding_tools). You MUST treat them as the
foundation of your `main.py`:
  - **Copy** every function you need verbatim into `main.py`.
  - **Inspect** each function's imports and third-party dependencies.
  - **Install** all required packages in an idempotent bootstrap section at the top of
    `main.py` (use `subprocess.check_call([sys.executable, "-m", "pip", "install", ...])`)
    so the fresh container has them before the functions are called.
  - Then call these functions in your own logic to accomplish the user task.

```
{coding_tools}
```

**Notice:** If no coding tools are provided, you must write your own code from scratch, designing both the structure and logic yourself.
</coding-tools>

<suggested-dependencies>
The user has suggested the following Python packages as preferred dependencies:
  {perf_libs}
If the list is non-empty, **always** include them in the bootstrap `pkgs` list.
They may be essential for the task or for the coding_tools above.

**Notice:** If no suggested dependencies are given, you must determine which packages to use based on the task.
</suggested-dependencies>

<how-to-write-main-py>
Your single program file is: `{output_path}/gen_codes/main.py`.

Structure it as follows:

```python
import subprocess, sys

# ── 1. Bootstrap: install ALL deps needed by coding_tools + your own code ──
def bootstrap():
    pkgs = ["pkg1", "pkg2", ...]  # from coding_tools imports + your needs + {perf_libs} (if any)
    for pkg in pkgs:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
bootstrap()

# ── 2. Paste coding_tools functions here (verbatim) ──
# def some_tool_function(...):
#     ...

# ── 3. Your solution code ──
# Use the coding_tools functions above to solve the user task.
# Save all outputs (charts, CSVs, etc.) to the current working directory
# (which is {output_path}/gen_codes/output at runtime).
```

Rules:
- Do NOT create alternate files (`main_v2.py`, `script.py`, `test.py`, etc.).
- Each run is a fresh container; installs do NOT persist. The bootstrap MUST run every time.
- Save all program outputs to the current working directory (cwd = output_path at runtime).
</how-to-write-main-py>

<how-to-run>
After writing or editing `main.py`, execute it:
  run_python_file("{output_path}/gen_codes/main.py", "{output_path}/gen_codes/output")
  - file_path: absolute path to the .py file.
  - output_path: directory where outputs go (also the cwd inside the container).
Then check the result. If it failed, fix `main.py` and run again.
</how-to-run>

<workspace-restrictions>
- Under `{output_path}/gen_codes`, you may ONLY have: `main.py` and `output/`.
- NEVER put or generate anything in the parent directory of {parent_of_output_path}.
- list_dir tool can **ONLY** be used in `{output_path}/gen_codes`.
</workspace-restrictions>

<before-stopping>
Reflect (keep it short):
1) Did `main.py` run successfully?
2) Did the output satisfy the user goal?
3) If not, what minimal change is needed before the next run?
</before-stopping>
</additional-instruction>
"""


class TinyCodingAgent(TinyAgent):

    def __init__(
        self,
        perf_libs: list[str] | None = None,
        coding_tools: list[Callable] | None = None,
        **kwargs,
    ):
        self.perf_libs = perf_libs or []
        self.coding_tools = coding_tools or []
        super().__init__(**kwargs)

    def get_main_work_instruction(self) -> str:
        coding_agent_instruction = CODING_AGENT_INSTRUCTION
        coding_agent_instruction = coding_agent_instruction.replace(
            "{output_path}", f"{self.output_location}"
        )
        coding_agent_instruction = coding_agent_instruction.replace(
            "{parent_of_output_path}", f"{os.path.dirname(self.output_location)}"
        )
        coding_agent_instruction = coding_agent_instruction.replace(
            "{perf_libs}", ", ".join(self.perf_libs)
        )
        coding_agent_instruction = coding_agent_instruction.replace(
            "{coding_tools}", "\n\n".join([str(t) for t in self.coding_tools])
        )
        return super().get_main_work_instruction(
            additional_instruction=coding_agent_instruction
        )

    def get_buildin_tools(self) -> list[Callable]:
        return super().get_buildin_tools() + [run_python_file]
