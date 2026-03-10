from typing import Union
from ollama import ChatResponse
from google.genai import types

AgentResponse = Union[types.GenerateContentResponse, ChatResponse, str, None]
