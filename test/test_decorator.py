import inspect

import pytest

from tiny_agent.subagent.decorator import subagent
from tiny_agent.tools.decorator import coding_tool, tool


def test_tool_decorator_preserves_docstring_but_str_does_not_include_it():
    def f():
        """doc-string: tool"""

        return "ok"

    decorated = tool()(f)

    assert inspect.getdoc(decorated) == "doc-string: tool"
    assert "doc-string: tool" not in str(decorated)


def test_coding_tool_str_includes_docstring_when_wrapping_plain_function():
    def f():
        """doc-string: coding_tool"""

        return "ok"

    decorated = coding_tool()(f)

    assert inspect.getdoc(f) == "doc-string: coding_tool"
    assert inspect.getdoc(decorated) != "doc-string: coding_tool"
    assert inspect.getdoc(inspect.unwrap(decorated)) == "doc-string: coding_tool"
    assert "doc-string: coding_tool" in str(decorated)


def test_coding_tool_str_includes_docstring_when_stacked_with_tool():
    @coding_tool()
    @tool()
    def f():
        """doc-string: stacked"""

        return "ok"

    assert inspect.getdoc(f) is None
    assert inspect.getdoc(inspect.unwrap(f)) == "doc-string: stacked"
    assert "doc-string: stacked" in str(f)


def test_subagent_str_is_class_docstring(tmp_path):
    from tiny_agent.agent.tiny_agent import TinyAgent

    @subagent
    class SA(TinyAgent):
        """doc-string: subagent"""

        pass

    agent = SA(
        name="sa",
        model="dummy",
        output_root=str(tmp_path),
        ollama_stuff={"host": "http://localhost:11434"},
    )

    assert inspect.getdoc(SA) == "doc-string: subagent"
    assert inspect.getdoc(agent) == "doc-string: subagent"
    assert str(agent) == "doc-string: subagent"
