import time
import uuid
from functools import wraps
from typing import Callable, Optional

from google import genai
from google.genai import types

from ..tools.buildins.core import (
    create_work_plan,
    read_memory,
    read_work_plan,
    reflect,
    update_memory,
    update_work_plan,
)
from ..tools.buildins.filesys import (
    append_to_file,
    file_exists,
    list_dir,
    read_file,
    write_file,
)
from ..tools.buildins.subagents_helper import transfer_to_subagent
from ..tools.buildins.utils import (
    get_current_datetime_in_local,
    get_current_datetime_in_utc,
)
from ..tools.decorator import _agent_info_context, tool
from .agent_manager import AgentManager

MAX_RETRY_ATTEMPTS = 5
SYSTEM_INSTRUCTION = """
You are an autonomous AI agent.
"""
INSTRUCTIONS = """
Complete task based on <instruction>.

<instruction>
- Before starting work, use create_work_plan to create a work-plan that outlines each step required to complete the task.
- Execute the steps in the work-plan **STEP-BY-STEP aka. ONE-BY-ONE**.
- **Always** use update_memory to record your actions after calling any tool or receiving response. **WARNING**: This does not include work-plan (step status) update actions, as work-plan has its own separate isolated storage mechanism.
- After completing a step of the work-plan, **always** use update_work_plan to update the status of that step in work-plan.   
- **Always** use reflect to perform reflection for decision-making, after updating a step status in work-plan. When reflecting, always include:
    1. What you have done **in detail**.
    2. What results you have obtained **in detail**.
    3. What you will do next **in detail**.
    4. Shall I stop working or continue to work **regarding the status of the steps in the work-plan**?
- **Always** use reflect to perform reflection for decision-making, after calling a tool. When reflecting, always include:
    1. Understand the tool call result. 
    2. What shall I do next **regarding the status of the steps in the work-plan**?
    3. Shall I stop working or continue to work **regarding the status of the steps in the work-plan**?
- **Always** use reflect to perform reflection for decision-making, after updating memory. When reflecting, always include:
    1. What shall I do next **regarding the status of the steps in the work-plan**?
    2. Shall I stop working or continue to work **regarding the status of the steps in the work-plan**?
- **IMPORTANT**: **Never** stop working before all steps in the work-plan are completed with ✅, check the actual work-plan status to determin:
    - Shall I stop?
        - If yes, stop working.
        - If no, continue to work.
</instruction>

<execute-step-rule>
- The work-plan shall be created only once if it currently does not exist and shall be operated according to the following protocol:
- The work-plan should be in a classic checklist format:
    - Each line starts with a checkbox indicating the status in square brackets
    - For completed items: [✅] followed by the task description
    - For incomplete items: [🟡] followed by the task description
    - For in-progress items: [🔄] followed by the task description
    - For failed items: [❌] followed by the task description 
    For example:
- [✅] Task 1
- [🟡] Task 2
- [🔄] Task 3
- [❌] Task 4
</execute-step-rule>
"""

SUB_AGENTS_FOOTNOTE = """
You have the following subagents that can help you:
{subagents}
Please **always** use the tool `transfer_to_subagent` to transfer the task to the sub-agent.
You pass the name of the sub-agent and the task to the tool.
**Always** use reflect to perform reflection for decision-making, before transferring the task to the sub-agent. When reflecting, always include:
1. Why shall I transfer the task to certain sub-agent?
2. Is the task description clear and complete? If not, an update the task description might be needed. 
"""


class TinyAgent:
    def __init__(
        self,
        name: str,
        model: str,
        output_root: str,
        tools: list[Callable] = list(),
        subagents: list["TinyAgent"] = list(),
        system_instruction: str = SYSTEM_INSTRUCTION,
        vertexai: bool = True,
        vertexai_project: str = None,
        vertexai_location: str = None,
        google_ai_studio_api_key=None,
        http_options: types.HttpOptions = types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        **kwargs,
    ):
        """
        Initialize the TinyAgent.

        Args:
            name: Agent name
            model: Model to use
            tools: List of tools
            output_root: Output root directory, final output location will be {output_root}/{name}-{agent_id}"
            system_instruction: System instruction
            vertexai: Whether to use Vertex AI
            vertexai_project: Vertex AI project
            vertexai_location: Vertex AI location
            google_ai_studio_api_key: Google AI Studio API key
            **kwargs: Additional arguments to model config.
        """
        if not name:
            # Agent name is required
            raise ValueError("Agent name is required")
        if not output_root:
            # Output root is required
            raise ValueError("Output root is required")
        if vertexai and not (vertexai_project and vertexai_location):
            raise ValueError(
                "vertexai_project and vertexai_location must be provided when vertexai is True"
            )
        if not vertexai and not google_ai_studio_api_key:
            raise ValueError(
                "google_ai_studio_api_key must be provided when vertexai is False"
            )
        self.vertexai = vertexai
        self.vertexai_project = vertexai_project
        self.vertexai_location = vertexai_location
        self.google_ai_studio_api_key = google_ai_studio_api_key
        longst_int_time = int(time.time())
        self.agent_id = f"{longst_int_time}-{str(uuid.uuid4())}"
        self.name = name
        self.model = model
        self.output_root = output_root
        self.output_location = f"{self.output_root}/{self.name}-{self.agent_id}"
        self.client = genai.Client(
            **(
                {
                    "vertexai": self.vertexai,
                    "project": self.vertexai_project,
                    "location": (
                        "global" if "-preview" in model else self.vertexai_location
                    ),
                }
                if self.vertexai
                else {
                    "api_key": self.google_ai_studio_api_key,
                }
            ),
        )
        builtin_tools = [
            create_work_plan,
            update_work_plan,
            read_work_plan,
            update_memory,
            read_memory,
            reflect,
            list_dir,
            read_file,
            write_file,
            append_to_file,
            file_exists,
            get_current_datetime_in_utc,
            get_current_datetime_in_local,
            transfer_to_subagent,
        ]
        all_tools = self._append_tools(builtin_tools, tools)
        # Create independent copies of tools to avoid shared state in concurrent execution
        # Each TinyAgent gets its own copy with its own _agent_info
        self.tools = []
        agent_info = {
            "agent_name": self.name,
            "agent_id": self.agent_id,
            "output_location": self.output_location,
        }
        for tool_func in all_tools:
            if hasattr(tool_func, "_agent_info"):
                # Create a wrapper that captures this agent's info
                tool_copy = self._create_tool_copy(tool_func, agent_info)
                self.tools.append(tool_copy)
            else:
                self.tools.append(tool_func)
        self.config = types.GenerateContentConfig(
            **{
                **{
                    "http_options": http_options,
                    "tools": self.tools,
                    "system_instruction": system_instruction,
                    "automatic_function_calling": types.AutomaticFunctionCallingConfig(
                        disable=False,
                        maximum_remote_calls=99999999,
                        ignore_call_history=False,
                    ),
                },
                **kwargs,
            }
        )
        self.subagents = self._append_subagents(dict(), subagents)
        AgentManager().register(self)

    def _append_tools(
        self, builtin_tools: list[Callable], upcoming_tools: list[Callable]
    ) -> list[Callable]:
        for t in upcoming_tools:
            if not callable(t):
                raise TypeError(f"{t} is not callable")
            if not hasattr(t, "_agent_info"):
                raise TypeError(
                    f"{t.__name__ if hasattr(t, '__name__') else t} is not decorated by @tool() from tiny_agent.tools.decorator"
                )

        return builtin_tools + upcoming_tools

    def _create_tool_copy(self, tool_func, agent_info: dict):
        """Create an independent copy of a tool with its own agent_info.

        This avoids shared state issues when multiple TinyAgents run concurrently.
        Uses ContextVar (_agent_info_context) which is thread-safe.
        """

        # Get the original unwrapped function
        original_func = (
            tool_func.__wrapped__ if hasattr(tool_func, "__wrapped__") else tool_func
        )

        @wraps(original_func)
        def tool_copy(*args, **kwargs):
            # Set agent_info in thread-safe ContextVar before calling the tool
            token = _agent_info_context.set(agent_info)
            try:
                return tool_func(*args, **kwargs)
            finally:
                _agent_info_context.reset(token)

        # Also set on the wrapper for backward compatibility
        tool_copy._agent_info = agent_info.copy()
        return tool_copy

    def _append_subagents(
        self,
        builtin_subagents: dict[str, "TinyAgent"],
        upcoming_subagents: list["TinyAgent"],
    ) -> dict[str, "TinyAgent"]:
        for subagent in upcoming_subagents:
            if not isinstance(subagent, TinyAgent):
                raise TypeError(f"{subagent} is not a TinyAgent instance")
            if not hasattr(subagent, "_is_async"):
                raise TypeError(
                    f"{subagent} is not decorated by @subagent() from tiny_agent.subagent.decorator"
                )
            if subagent.name == self.name:
                raise ValueError(
                    f"Subagent name '{subagent.name}' cannot be the same as the parent agent name"
                )
        return {
            **builtin_subagents,
            **{subagent.name: subagent for subagent in upcoming_subagents},
        }

    def get_subagent_by_name(self, name: str) -> Optional["TinyAgent"]:
        return self.subagents.get(name)

    @property
    def subagents_count(self) -> int:
        return len(self.subagents)

    def __call__(self, contents, **kwargs) -> types.GenerateContentResponse:
        """Call the agent with the given contents and optional keyword arguments.

        Args:
            contents: The contents to pass to the agent.
            **kwargs: A dict try to override the current modelconfig.
        """
        if kwargs:
            self.config = types.GenerateContentConfig(
                **{**self.config.model_dump(exclude_none=True), **kwargs}
            )

        prompt = f"""{contents}
           
{INSTRUCTIONS}

{SUB_AGENTS_FOOTNOTE.format(subagents={name: str(agent) for name, agent in self.subagents.items()}) if self.subagents_count > 0 else ""}
""".strip()

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.config,
        )
        return response
