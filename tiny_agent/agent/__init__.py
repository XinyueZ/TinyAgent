from typing import Union

from google.genai import types
from ollama import ChatResponse

from .tiny_agent import TinyAgent

AgentResponse = Union[types.GenerateContentResponse, ChatResponse, str, None]

__all__ = ["AgentResponse", "TinyAgent"]
