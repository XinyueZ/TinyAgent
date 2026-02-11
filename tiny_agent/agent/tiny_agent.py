from functools import wraps
from ..tools.decorator import _agent_info_context
from typing import Any
import uuid
from google import genai
from google.genai import types
import time
from ..tools.buildin_tools import (
    create_work_plan,
    update_work_plan,
    read_work_plan,
    update_memory,
    read_memory,
    reflect,
    read_file,
    write_file,
    append_to_file,
    file_exists,
    get_current_datetime_in_utc,
    get_current_datetime_in_local,
)


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


class TinyAgent:
    def __init__(
        self,
        name: str,
        model: str,
        tools: list[Any],
        output_root: str,
        system_instruction: str = SYSTEM_INSTRUCTION,
        vertexai: bool = True,
        vertexai_project: str = None,
        vertexai_location: str = None,
        google_ai_studio_api_key=None,
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
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=MAX_RETRY_ATTEMPTS),
            ),
        )
        builtin_tools = [
            create_work_plan,
            update_work_plan,
            read_work_plan,
            update_memory,
            read_memory,
            reflect,
            read_file,
            write_file,
            append_to_file,
            file_exists,
            get_current_datetime_in_utc,
            get_current_datetime_in_local,
        ]
        all_tools = builtin_tools + list(tools)
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
            tools=self.tools,
            system_instruction=system_instruction,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False,
                maximum_remote_calls=99999999,
                ignore_call_history=False,
            ),
            **kwargs,
        )

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

    def __call__(self, contents, **kwargs):
        """Call the agent with the given contents and optional keyword arguments.

        Args:
            contents: The contents to pass to the agent.
            **kwargs: A dict try to override the current modelconfig.
        """
        if kwargs:
            self.config = {**self.config, **kwargs}

        response = self.client.models.generate_content(
            model=self.model,
            contents=f"""{contents}
           
{INSTRUCTIONS}
""",
            config=self.config,
        )
        return response
