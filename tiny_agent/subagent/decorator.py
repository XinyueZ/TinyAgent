def subagent(_cls=None, *, is_async: bool = False):
    """Class decorator that marks a TinyAgent subclass as a sub-agent.

    Supports both ``@subagent`` and ``@subagent()`` / ``@subagent(is_async=True)``.

    Args:
        is_async: Whether this sub-agent runs asynchronously.

    Raises:
        TypeError: If the decorated class is not a subclass of TinyAgent.

    Example::

        @subagent
        class AddAgent(TinyAgent):
            \"\"\"Perform addition.\"\"\"
            ...

        @subagent()
        class SubAgent(TinyAgent):
            \"\"\"Perform subtraction.\"\"\"
            ...

        @subagent(is_async=True)
        class ResearchAgent(TinyAgent):
            \"\"\"A research sub-agent that performs web searches.\"\"\"
            ...

        agent = ResearchAgent(name="research", model="gemini-2.5-flash-lite", ...)
        str(agent)        # → "A research sub-agent that performs web searches."
        agent._is_async   # → True
    """

    def decorator(cls):
        from tiny_agent.agent.tiny_agent import TinyAgent

        if not issubclass(cls, TinyAgent):
            raise TypeError(
                f"@subagent can only be applied to subclasses of TinyAgent, "
                f"but {cls.__name__} is not."
            )

        cls._is_async = is_async

        def __str__(self):
            return cls.__doc__ or ""

        cls.__str__ = __str__

        return cls

    if _cls is not None:
        return decorator(_cls)
    return decorator
