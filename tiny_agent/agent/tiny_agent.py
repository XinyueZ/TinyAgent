import copy
import os
import threading
import time
import uuid
from functools import wraps
from typing import Any, Callable, Optional

from google.genai import types
from ollama import ChatResponse
from typing_extensions import TypedDict
from pydantic import BaseModel

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
from ..tools.buildins.subagents_helper import (
    transfer_to_subagent,
    transfer_to_subagents,
)
from ..tools.buildins.utils import (
    get_current_datetime_in_local,
    get_current_datetime_in_utc,
)
from ..tools.decorator import _agent_info_context
from .agent_manager import AgentManager
from .ollama_utils import ollama_automatic_function_calling

MAX_RETRY_ATTEMPTS = 5

SYSTEM_INSTRUCTION = """
You are an autonomous AI agent.
"""

SUBAGENT_HEADNOTE = """
{subagent_instruction}
**ALWAYS** when you have completed, please save the report to file (if the user **does not specify a storage mechanism**, always use this): {output_path}
**Reflect** on yourself to check if the report file exists. If it does not, redo the save operation to save the report to the file. If the file exists, stop working.
"""

AGENT_WORK_INSTRUCTIONS = """
Complete task based on <instruction>.

<instruction>
- **Always** At the very beginning, use create_work_plan to create a work-plan that outlines each step required to complete the task.
- **Always** Execute the steps in the work-plan **STEP-BY-STEP aka. ONE-BY-ONE**.
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
""".strip()

STORAGE_INSTRUCTION = """
We have the following default storage mechanisms in filesystem (if the user **does not specify a storage mechanism**, always use those default ones):
<storage-instruction>
Work-plan storage: {work_plan_storage}
Memory storage: {memory_storage}
Reflection storage: {reflection_storage}
Are you a subagent? {is_subagent}, 
- if **yes (true)**, you have storage to save your work result: {subagent_result_storage}
- if **no (false)**, the work-result storage could be specified by the user based on the task description.
</storage-instruction>
"""

SUBAGENTS_FOOTNOTE = """
You have the following subagents that can help you:
{subagents}

<transfer-to-subagent-rule>
You have two transfer patterns to choose from:

1. **ONE-TO-ONE** (`transfer_to_subagent`): Transfer a task to a single sub-agent. Pass the sub-agent's name as a string. Use this when only one sub-agent is needed for the task.
2. **ONE-TO-MANY** (`transfer_to_subagents`): Transfer a task to multiple sub-agents in parallel. Pass a list of sub-agent names. Use this when multiple sub-agents can work on the same task or different aspects of the task concurrently. Only sub-agents marked with `is_async=True` can be used with this pattern.

**Always** use reflect to perform reflection for decision-making, before transferring. When reflecting, always include:
1. Do I need one sub-agent or multiple sub-agents for this task?
2. If multiple, can they work in parallel on the same task, or do they depend on each other's results?
   - If they can work in parallel → use `transfer_to_subagents` (ONE-TO-MANY).
   - If they depend on each other → use `transfer_to_subagent` (ONE-TO-ONE) sequentially.
3. Why shall I transfer the task to certain sub-agent(s)?
4. Is the task description clear and complete? If not, update the task description before transferring.

**Always**: Wait until all sub-agents have completed their tasks before proceeding next step.
**Always**: When transferring, introduce yourself clearly: "I am [xxxxxx]. My task or row is [yyyyy], now I need [specific request]..."
</transfer-to-subagent-rule>
""".strip()


class GenaiStuffDict(TypedDict, total=False):
    system_instruction: Optional[str]
    vertexai: Optional[bool]
    vertexai_project: Optional[str]
    vertexai_location: Optional[str]
    google_ai_studio_api_key: Optional[str]
    http_options: Optional[types.HttpOptions]


GENAI_STUFF_DEFAULTS: GenaiStuffDict = {
    "system_instruction": SYSTEM_INSTRUCTION,
    "http_options": types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=3)),
}


class OllamaStuffDict(TypedDict, total=False):
    system_instruction: Optional[str]
    host: Optional[str]


OLLAMA_STUFF_DEFAULTS: OllamaStuffDict = {
    "system_instruction": SYSTEM_INSTRUCTION,
}


class TinyAgent:

    def __init__(
        self,
        name: str,
        model: str,
        output_root: str,
        genai_stuff: GenaiStuffDict | None = None,
        ollama_stuff: OllamaStuffDict | None = None,
        tools: list[Callable | BaseModel] | None = None,
        subagents: list["TinyAgent"] | None = None,
        **kwargs,
    ):
        """
        Initialize the TinyAgent.

        Args:
            name: Agent name.
            model: Model to use for generation.
            output_root: Output root directory, final output location will be {output_root}/{name}-{agent_id}.
            tools: List of callable tools available to the agent.
            subagents: List of TinyAgent subagents for hierarchical task delegation.
            genai_stuff: Configuration dict for Google GenAI (Vertex AI or AI Studio).
            ollama_stuff: Configuration dict for Ollama.
            **kwargs: Additional arguments passed to model config.
        """
        if not name:
            # Agent name is required
            raise ValueError("Agent name is required")
        if not output_root:
            # Output root is required
            raise ValueError("Output root is required")

        if not genai_stuff and not ollama_stuff:
            raise ValueError("genai_stuff or ollama_stuff must be provided")
        if genai_stuff and ollama_stuff:
            raise ValueError(
                "genai_stuff and ollama_stuff cannot be provided at the same time"
            )

        tools = tools or []
        subagents = subagents or []

        self.genai_stuff = None
        if genai_stuff:
            if genai_stuff.get("vertexai") and not (
                genai_stuff.get("vertexai_project")
                and genai_stuff.get("vertexai_location")
            ):
                raise ValueError(
                    "vertexai_project and vertexai_location must be provided when vertexai is True"
                )
            if not genai_stuff.get("vertexai") and not genai_stuff.get(
                "google_ai_studio_api_key"
            ):
                raise ValueError(
                    "google_ai_studio_api_key must be provided when vertexai is False"
                )
            self.genai_stuff = {**self.get_default_genai_stuff(), **genai_stuff}

        self.ollama_stuff = None
        if ollama_stuff:
            self.ollama_stuff = {**self.get_default_ollama_stuff(), **ollama_stuff}

        self.is_subagent = hasattr(self, "_is_async")

        self._owner_thread_id = threading.get_ident()

        longst_int_time = int(time.time() * 1000000)
        self.agent_id = f"{longst_int_time}-{str(uuid.uuid4())}"
        self.name = name
        self.model = model
        self.output_root = output_root
        self.output_location = f"{self.output_root}/{self.name}-{self.agent_id}"

        if self.genai_stuff:
            from google import genai

            self.client = genai.Client(
                **(
                    {
                        "vertexai": self.genai_stuff["vertexai"],
                        "project": self.genai_stuff["vertexai_project"],
                        "location": (
                            "global"
                            if "-preview" in model
                            else self.genai_stuff["vertexai_location"]
                        ),
                    }
                    if self.genai_stuff.get("vertexai")
                    else {
                        "api_key": self.genai_stuff["google_ai_studio_api_key"],
                    }
                ),
            )

        if self.ollama_stuff:
            from ollama import Client

            self.client = Client(host=self.ollama_stuff.get("host"))

        agent_info = self.create_agent_info()
        builtin_tools = self.get_buildin_tools()
        all_tools = self._append_tools(builtin_tools, tools)
        # Create independent copies of tools to avoid shared state in concurrent execution
        # Each TinyAgent gets its own copy with its own _agent_info
        self.tools = []
        for tool_func in all_tools:
            if isinstance(tool_func, BaseModel):
                # This situation is very likely due to Google build-in tool
                # https://ai.google.dev/gemini-api/docs/tools
                # We don't track it.
                self.tools.append(tool_func)
            elif hasattr(tool_func, "_agent_info"):
                # Create a wrapper that captures this agent's info
                tool_copy = self._create_tool_copy(tool_func, agent_info)
                self.tools.append(tool_copy)
            else:
                self.tools.append(tool_func)
        if self.genai_stuff:
            self.genai_stuff["config"] = types.GenerateContentConfig(
                **{
                    **{
                        "http_options": self.genai_stuff.get("http_options"),
                        "tools": self.tools,
                        "system_instruction": self.genai_stuff.get(
                            "system_instruction"
                        ),
                        "automatic_function_calling": types.AutomaticFunctionCallingConfig(
                            disable=False,
                            maximum_remote_calls=99999999,
                            ignore_call_history=False,
                        ),
                    },
                    **kwargs,
                }
            )

        if self.ollama_stuff:
            from functools import partial

            self.ollama_stuff["config"] = partial(
                ollama_automatic_function_calling,
                self.client.chat,
                model=self.model,
                max_turns=99999999,
                tools=self.tools,
                **kwargs,
            )

        buildin_subagents = dict()
        self.subagents = self._append_subagents(buildin_subagents, subagents)

        AgentManager().register(self)

    def create_agent_info(self) -> dict[str, Any]:
        return {
            "agent_name": self.name,
            "agent_id": self.agent_id,
            "output_location": self.output_location,
        }

    def _append_tools(
        self,
        builtin_tools: list[Callable | BaseModel],
        upcoming_tools: list[Callable | BaseModel],
    ) -> list[Callable | BaseModel]:
        for t in upcoming_tools:
            if not callable(t) and not isinstance(t, BaseModel):
                raise TypeError(
                    f"{t} is not callable or BaseModel(Google Build-in Tool)"
                )
            if not hasattr(t, "_agent_info") and not isinstance(t, BaseModel):
                raise TypeError(
                    f"{t.__name__ if hasattr(t, '__name__') else t} is not decorated by @tool() from tiny_agent.tools.decorator OR is not a build-in tool from Google"
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
            for existing_name in builtin_subagents:
                if subagent.name == existing_name:
                    raise ValueError(
                        f"Subagent name '{subagent.name}' conflicts with an existing subagent"
                    )
            for other_subagent in upcoming_subagents:
                if (
                    subagent is not other_subagent
                    and subagent.name == other_subagent.name
                ):
                    raise ValueError(
                        f"Duplicate subagent name '{subagent.name}' found in upcoming subagents"
                    )

        return {
            **builtin_subagents,
            **{subagent.name: subagent for subagent in upcoming_subagents},
        }

    def append_subagents(self, subagent: "TinyAgent"):
        if not hasattr(subagent, "_is_async"):
            raise TypeError(
                f"{subagent} is not decorated by @subagent() from tiny_agent.subagent.decorator"
            )
        if subagent.name == self.name:
            raise ValueError(
                f"Subagent name '{subagent.name}' cannot be the same as the parent agent name"
            )

        if subagent.name in self.subagents:
            raise ValueError(f"Subagent name '{subagent.name}' already exists")

        self.subagents[subagent.name] = subagent

    def get_subagent_by_name(self, name: str) -> Optional["TinyAgent"]:
        return self.subagents.get(name)

    @property
    def subagents_count(self) -> int:
        return len(self.subagents)

    def get_buildin_tools(self) -> list[Callable | BaseModel]:
        return [
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
            transfer_to_subagents,
        ]

    def get_default_genai_stuff(self) -> GenaiStuffDict:
        return copy.deepcopy(GENAI_STUFF_DEFAULTS)

    def get_default_ollama_stuff(self) -> OllamaStuffDict:
        return dict(OLLAMA_STUFF_DEFAULTS)

    def get_main_work_instruction(self, additional_instruction: str = "") -> str:
        if additional_instruction:
            return (AGENT_WORK_INSTRUCTIONS + "\n\n" + additional_instruction).strip()

        return AGENT_WORK_INSTRUCTIONS

    def __call__(
        self, contents: str, **kwargs
    ) -> types.GenerateContentResponse | ChatResponse | None:
        """Call the agent with the given contents and optional keyword arguments.

        Args:
            contents: The contents string to pass to the agent.
            **kwargs: A dict try to override the current modelconfig.
        """

        if threading.get_ident() != self._owner_thread_id:
            raise RuntimeError(
                "TinyAgent instance is not thread-safe; calling __call__ from a different thread is not allowed"
            )

        prompt = f"""
{SUBAGENT_HEADNOTE.format(subagent_instruction=self.__str__(), output_path=os.path.join(self.output_location, "result.md")) if self.is_subagent else ""}

{contents.strip()}
           
{self.get_main_work_instruction().strip()}

{STORAGE_INSTRUCTION.format(work_plan_storage=os.path.join(self.output_location, "work_plan.md"), memory_storage=os.path.join(self.output_location, "memory.md"), reflection_storage=os.path.join(self.output_location, "reflection.md"), is_subagent=self.is_subagent, subagent_result_storage=os.path.join(self.output_location, "result.md") if self.is_subagent else "")}

{SUBAGENTS_FOOTNOTE.format(subagents={name: str(agent) for name, agent in self.subagents.items()}) if self.subagents_count > 0 else ""}
""".strip()

        if self.genai_stuff:
            if kwargs:
                self.genai_stuff["config"] = types.GenerateContentConfig(
                    **{
                        **self.genai_stuff["config"].model_dump(exclude_none=True),
                        **kwargs,
                    }
                )

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.genai_stuff["config"],
            )
            return response

        if self.ollama_stuff:
            if kwargs:
                from functools import partial

                self.ollama_stuff["config"] = partial(
                    ollama_automatic_function_calling,
                    self.client.chat,
                    model=self.model,
                    max_turns=99999999,
                    tools=self.tools,
                    **kwargs,
                )

            messages = [
                {"role": "system", "content": self.ollama_stuff["system_instruction"]},
                {"role": "user", "content": prompt},
            ]
            response, _ = self.ollama_stuff["config"](messages=messages)
            return response

        raise ValueError("Neither genai nor ollama stuff is specified")
