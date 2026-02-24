import threading
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from tiny_agent.agent.tiny_agent import TinyAgent


class AgentManager:
    _instance: Optional["AgentManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "AgentManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._agents: Dict[str, "TinyAgent"] = {}
                    cls._instance._agents_lock = threading.Lock()
        return cls._instance

    def get_agent_by_name(self, name: str) -> "TinyAgent":
        with self._agents_lock:
            for agent in self._agents.values():
                if agent.name == name:
                    return agent

    def register(self, tiny_agent: "TinyAgent") -> None:
        with self._agents_lock:
            for existing in self._agents.values():
                if existing.name == tiny_agent.name:
                    raise ValueError(
                        f"An agent with name '{tiny_agent.name}' is already registered "
                        f"(agent_id: {existing.agent_id}). Agent names must be unique."
                    )
            self._agents[tiny_agent.agent_id] = tiny_agent

    def unregister(self, agent_id: str) -> None:
        with self._agents_lock:
            self._unregister_recursive(agent_id)

    def _unregister_recursive(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent is not None:
            for sa in agent.subagents.values():
                self._unregister_recursive(sa.agent_id)
            del self._agents[agent_id]
