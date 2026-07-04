# tests/test_tools.py - fixed: no sys.modules poisoning
import json
import pytest
from unittest.mock import MagicMock, patch


class FakeToolCall:
    def __init__(self, name, arguments):
        self.function = FakeFunction(name, arguments)


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = json.dumps(arguments)


class TestToolRegistry:
    def test_register_creates_metadata(self):
        from agent.tools import ToolRegistry
        reg = ToolRegistry()

        @reg.register
        def test_tool(param1: str, param2: int = 0):
            """a test tool."""
            return f"{param1}-{param2}"

        assert len(reg.tools_metadata) == 1
        meta = reg.tools_metadata[0]
        assert meta["type"] == "function"
        assert meta["function"]["name"] == "test_tool"
        assert "param1" == meta["function"]["parameters"]["required"][0]
        assert "param2" not in meta["function"]["parameters"]["required"]

    def test_register_no_type_hints_defaults_to_string(self):
        from agent.tools import ToolRegistry
        reg = ToolRegistry()

        @reg.register
        def no_hint_tool(x):
            return x

        meta = reg.tools_metadata[0]
        assert meta["function"]["parameters"]["properties"]["x"]["type"] == "string"

    def test_handle_calls_registered_function(self):
        from agent.tools import ToolRegistry
        reg = ToolRegistry()

        @reg.register
        def add(a: int, b: int):
            return a + b

        result = reg.handle(FakeToolCall("add", {"a": 3, "b": 4}))
        assert result == 7

    def test_handle_unknown_function(self):
        from agent.tools import ToolRegistry
        reg = ToolRegistry()
        result = reg.handle(FakeToolCall("nonexistent", {}))
        assert "error" in str(result).lower() or "未定义" in result or "错误" in result

    def test_multiple_registrations(self):
        from agent.tools import ToolRegistry
        reg = ToolRegistry()

        @reg.register
        def f1():
            pass

        @reg.register
        def f2():
            pass

        assert len(reg.functions) == 2
        assert "f1" in reg.functions
        assert "f2" in reg.functions

    def test_list_files_tool_returns_string(self, test_inputs_dir):
        with patch("agent.tools.brain", MagicMock()), \
             patch("agent.tools.logger", MagicMock()):
            from agent.tools import list_files
            result = list_files(test_inputs_dir)
            assert isinstance(result, str)
            assert "clean.txt" in result
            assert "violation.txt" in result

    def test_list_files_nonexistent_dir(self):
        with patch("agent.tools.brain", MagicMock()), \
             patch("agent.tools.logger", MagicMock()):
            from agent.tools import list_files
            result = list_files("nonexistent_dir_xyz")
            assert isinstance(result, str)

    def test_get_current_time_returns_string(self):
        with patch("agent.tools.brain", MagicMock()), \
             patch("agent.tools.logger", MagicMock()):
            from agent.tools import get_current_time
            result = get_current_time()
            assert isinstance(result, str)
            assert len(result) == 19
            assert ":" in result
