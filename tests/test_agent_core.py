# tests/test_agent_core.py - fixed: use patch() instead of sys.modules poisoning
import pytest
from unittest.mock import MagicMock, patch


class TestSanitizeObservation:
    def test_normal_data_passes_through(self):
        with patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import sanitize_observation
            result = sanitize_observation("hello world", "some_tool", {})
            assert "hello world" in result
            assert "some_tool" in result

    def test_garbled_data_detected(self):
        with patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import sanitize_observation
            garbled = "aB3dEfGhIjKlMnOpQrStUvWxYz0123456789"
            result = sanitize_observation(garbled, "reader", {})
            assert "System Error" in result or "异常" in result

    def test_read_file_tool_adds_anchor(self):
        with patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import sanitize_observation
            result = sanitize_observation(
                "file content here",
                "read_file_tool",
                {"file_path": "docs/report.txt"}
            )
            assert "docs/report.txt" in result
            assert "file content here" in result

    def test_read_file_tool_missing_path(self):
        with patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import sanitize_observation
            result = sanitize_observation("content", "read_file_tool", {})
            assert "content" in result

    def test_non_string_data_converted(self):
        with patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import sanitize_observation
            result = sanitize_observation(12345, "counter", {})
            assert "12345" in result

    def test_none_data(self):
        with patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import sanitize_observation
            result = sanitize_observation(None, "checker", {})
            assert "None" in result


class TestValidateFencingToken:
    def test_token_greater_than_latest_passes(self):
        mock_brain = MagicMock()
        mock_brain.get_latest_token_from_db.return_value = 5
        with patch("agent.agent_core.brain", mock_brain), \
             patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import validate_fencing_token
            assert validate_fencing_token(10) is True

    def test_token_equal_to_latest_passes(self):
        mock_brain = MagicMock()
        mock_brain.get_latest_token_from_db.return_value = 5
        with patch("agent.agent_core.brain", mock_brain), \
             patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import validate_fencing_token
            assert validate_fencing_token(5) is True

    def test_token_less_than_latest_fails(self):
        mock_brain = MagicMock()
        mock_brain.get_latest_token_from_db.return_value = 10
        with patch("agent.agent_core.brain", mock_brain), \
             patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import validate_fencing_token
            assert validate_fencing_token(3) is False

    def test_token_when_db_is_empty(self):
        mock_brain = MagicMock()
        mock_brain.get_latest_token_from_db.return_value = 0
        with patch("agent.agent_core.brain", mock_brain), \
             patch("agent.agent_core.logger", MagicMock()):
            from agent.agent_core import validate_fencing_token
            assert validate_fencing_token(1) is True


class TestRunAgentLoopIntegration:
    def test_loop_terminates_with_text_response(self):
        mock_brain = MagicMock()
        mock_logger = MagicMock()
        mock_client = MagicMock()
        mock_registry = MagicMock()

        mock_msg = MagicMock()
        mock_msg.content = "audit complete, no issues found"
        mock_msg.tool_calls = None
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=mock_msg)]
        )

        with patch("agent.agent_core.brain", mock_brain), \
             patch("agent.agent_core.logger", mock_logger), \
             patch("agent.agent_core.client", mock_client), \
             patch("agent.agent_core.registry", mock_registry), \
             patch("agent.agent_core.MAX_STEPS", 5):
            from agent.agent_core import run_agent_loop
            run_agent_loop("check inputs folder", task_id="test_integration")
            assert mock_brain.save_episodic.called
            assert mock_brain.auto_compress.called

    def test_loop_handles_exception_gracefully(self):
        mock_brain = MagicMock()
        mock_logger = MagicMock()
        mock_client = MagicMock()
        mock_registry = MagicMock()

        mock_client.chat.completions.create.side_effect = RuntimeError("API down")

        with patch("agent.agent_core.brain", mock_brain), \
             patch("agent.agent_core.logger", mock_logger), \
             patch("agent.agent_core.client", mock_client), \
             patch("agent.agent_core.registry", mock_registry):
            from agent.agent_core import run_agent_loop
            run_agent_loop("test", task_id="test_error")
            assert mock_logger.error.called

    def test_loop_hits_max_steps(self):
        mock_brain = MagicMock()
        mock_logger = MagicMock()
        mock_client = MagicMock()
        mock_registry = MagicMock()

        mock_brain.get_latest_token_from_db.return_value = 0

        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "list_files"
        mock_tool_call.function.arguments = '{"directory": "inputs"}'

        mock_msg = MagicMock()
        mock_msg.content = "checking files"
        mock_msg.tool_calls = [mock_tool_call]

        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=mock_msg)]
        )
        mock_registry.handle.return_value = "['clean.txt']"
        mock_registry.tools_metadata = []

        with patch("agent.agent_core.brain", mock_brain), \
             patch("agent.agent_core.logger", mock_logger), \
             patch("agent.agent_core.client", mock_client), \
             patch("agent.agent_core.registry", mock_registry), \
             patch("agent.agent_core.MAX_STEPS", 3):
            from agent.agent_core import run_agent_loop
            run_agent_loop("scan all", task_id="test_max_steps")
            call_count = mock_client.chat.completions.create.call_count
            assert call_count <= 3
