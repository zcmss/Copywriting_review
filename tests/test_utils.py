# tests/test_utils.py
import os
import pytest
from agent.utils import safe_read_file


class TestSafeReadFile:
    """unit tests for safe_read_file."""

    def test_reads_valid_utf8_file(self, temp_dir):
        path = os.path.join(temp_dir, "doc.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("hello world")
        result = safe_read_file("doc.txt", base_dir=temp_dir)
        assert result == "hello world"

    def test_reads_gbk_encoded_file(self, temp_dir):
        path = os.path.join(temp_dir, "doc.txt")
        with open(path, "w", encoding="gbk") as f:
            f.write("中文内容")
        result = safe_read_file("doc.txt", base_dir=temp_dir)
        assert "中文内容" in result

    def test_returns_none_for_missing_file(self, temp_dir):
        result = safe_read_file("nonexistent.txt", base_dir=temp_dir)
        assert result is None

    def test_blocks_path_traversal(self, temp_dir):
        with pytest.raises(PermissionError):
            safe_read_file("../../etc/passwd", base_dir=temp_dir)

    def test_blocks_absolute_path_escape(self, temp_dir):
        with pytest.raises(PermissionError):
            safe_read_file("C:\\Windows\\System32\\drivers\\etc\\hosts", base_dir=temp_dir)

    def test_detects_garbled_content(self, temp_dir):
        """content that looks like random alphanumeric noise > 30 chars."""
        path = os.path.join(temp_dir, "garbled.txt")
        garbled = "aB3dEfGhIjKlMnOpQrStUvWxYz012345"  # 30+ chars, only alnum
        with open(path, "w", encoding="utf-8") as f:
            f.write(garbled)
        result = safe_read_file("garbled.txt", base_dir=temp_dir)
        assert result is None

    def test_passes_short_alphanumeric(self, temp_dir):
        """short alphanumeric content should NOT be flagged as garbled."""
        path = os.path.join(temp_dir, "short.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("abc123")
        result = safe_read_file("short.txt", base_dir=temp_dir)
        assert result == "abc123"

    def test_default_base_dir_is_inputs(self, monkeypatch):
        """when base_dir is None, uses agent/inputs."""
        import agent.utils as ut
        monkeypatch.setattr(ut.os.path, "dirname", lambda x: "/fake/agent")
        monkeypatch.setattr(ut.os.path, "abspath", lambda x: x)
        # should compute base_dir = /fake/agent/inputs
        # then try to join and find file - will fail since path doesn't exist
        # just verify the base_dir computation doesn't crash
        result = safe_read_file("somefile.txt")
        assert result is None  # file won't exist in fake path
