# tests/test_memory.py - fix last test
import hashlib
import pytest
from unittest.mock import MagicMock

mock_client = MagicMock()

import sys
sys.modules["agent.api_client"] = MagicMock()
sys.modules["agent.api_client"].client = mock_client

from agent.memory import UnifiedAgentMemory


class TestUnifiedAgentMemory:

    @pytest.fixture
    def brain(self):
        return UnifiedAgentMemory(client=mock_client, db_path=":memory:")

    def test_save_and_retrieve_episodic(self, brain):
        brain.save_episodic("task1", "user", "hello")
        brain.save_episodic("task1", "assistant", "world")
        ctx = brain.get_full_context("task1", "audit")
        episodic = ctx[1:]
        assert len(episodic) == 2
        assert episodic[0]["role"] == "user"
        assert episodic[0]["content"] == "hello"

    def test_episodic_task_isolation(self, brain):
        brain.save_episodic("task1", "user", "a")
        brain.save_episodic("task2", "user", "b")
        ctx1 = brain.get_full_context("task1")
        ctx2 = brain.get_full_context("task2")
        assert len(ctx1[1:]) == 1
        assert ctx1[1]["content"] == "a"

    def test_save_semantic_appears_in_context(self, brain):
        brain.save_semantic("rule1", "forbid keyword")
        ctx = brain.get_full_context("task1")
        system = ctx[0]["content"]
        assert "forbid keyword" in system

    def test_semantic_upsert(self, brain):
        brain.save_semantic("rule1", "v1")
        brain.save_semantic("rule1", "v2")
        rows = brain.conn.execute(
            "SELECT fact FROM semantic_memory WHERE entity = 'rule1'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "v2"

    def test_save_procedural_in_context(self, brain):
        brain.save_procedural("audit", "step1: scan\nstep2: read")
        ctx = brain.get_full_context("task1", "audit")
        system = ctx[0]["content"]
        assert "step1: scan" in system

    def test_missing_procedural_fallback(self, brain):
        ctx = brain.get_full_context("task1", "nonexistent_type")
        system = ctx[0]["content"]
        assert "未定义" in system

    def test_save_sensory_in_context(self, brain):
        brain.save_sensory("task1", "files: [a.txt, b.txt]")
        ctx = brain.get_full_context("task1")
        system = ctx[0]["content"]
        assert "a.txt" in system

    def test_sensory_returns_latest(self, brain):
        brain.save_sensory("task1", "first scan")
        brain.save_sensory("task1", "second scan")
        ctx = brain.get_full_context("task1")
        system = ctx[0]["content"]
        assert "second scan" in system

    def test_update_file_snapshot(self, brain):
        content = "test content"
        brain.update_file_snapshot("file.txt", content)
        expected_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        row = brain.conn.execute(
            "SELECT hash FROM file_snapshots WHERE file_path = ?", ("file.txt",)
        ).fetchone()
        assert row[0] == expected_hash

    def test_verify_snapshot_match(self, brain):
        content = "same content"
        brain.update_file_snapshot("f.txt", content)
        ok, h = brain.verify_snapshot("f.txt", content)
        assert ok is True

    def test_verify_snapshot_mismatch(self, brain):
        brain.update_file_snapshot("f.txt", "original")
        ok, old_hash = brain.verify_snapshot("f.txt", "modified")
        assert ok is False
        assert old_hash is not None

    def test_verify_snapshot_no_record(self, brain):
        ok, h = brain.verify_snapshot("nonexistent.txt", "content")
        assert ok is True
        assert h is not None

    def test_get_latest_token_defaults_to_zero(self, brain):
        assert brain.get_latest_token_from_db() == 0

    def test_increment_fencing_token(self, brain):
        brain.increment_fencing_token()
        assert brain.get_latest_token_from_db() == 1
        brain.increment_fencing_token()
        assert brain.get_latest_token_from_db() == 2

    def test_auto_compress_below_threshold_does_nothing(self, brain):
        brain.save_episodic("task1", "user", "msg1")
        brain.save_episodic("task1", "assistant", "msg2")
        brain.auto_compress("task1", threshold=10)
        count = brain.conn.execute(
            "SELECT COUNT(*) FROM episodic_memory WHERE task_id = 'task1' AND is_compressed = 0"
        ).fetchone()[0]
        assert count == 2

    def test_auto_compress_reaches_threshold_calls_llm(self, brain):
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="compressed summary"))]
        )
        for i in range(5):
            brain.save_episodic("task1", "user", f"msg{i}")
        brain.auto_compress("task1", threshold=3)
        compressed_count = brain.conn.execute(
            "SELECT COUNT(*) FROM episodic_memory WHERE task_id = 'task1' AND is_compressed = 1"
        ).fetchone()[0]
        assert compressed_count == 5
        summary_count = brain.conn.execute(
            "SELECT COUNT(*) FROM episodic_memory WHERE task_id = 'task1' AND is_compressed = 0"
        ).fetchone()[0]
        assert summary_count == 1

    def test_get_full_context_has_all_sections(self, brain):
        brain.save_procedural("audit", "do step")
        brain.save_semantic("r1", "no bad words")
        brain.save_sensory("task1", "env ok")
        brain.save_episodic("task1", "user", "check this")
        ctx = brain.get_full_context("task1", "audit")
        system = ctx[0]
        assert isinstance(system, dict)
        assert system["role"] == "system"
        assert "SOP" in system["content"] or "do step" in system["content"]
