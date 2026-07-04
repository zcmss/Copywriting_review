# tests/test_knowledge_base.py
"""RAG knowledge base unit + integration tests."""
import hashlib
import pytest
from chromadb.api.types import Documents, Embeddings
from chromadb.utils import embedding_functions


class DummyEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Fake embedder returning deterministic vectors, no model download needed."""

    def __call__(self, input: Documents) -> Embeddings:
        # each doc gets a vector based on hash of its text
        result = []
        for doc in input:
            h = int(hashlib.md5(doc.encode()).hexdigest()[:8], 16)
            result.append([(h >> i) & 1 for i in range(128)])
        return result


class TestChunkText:
    def test_short_text_single_chunk(self):
        from agent.knowledge_base import KnowledgeBase
        chunks = KnowledgeBase.chunk_text("short text", chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "short text"

    def test_long_text_multiple_chunks(self):
        from agent.knowledge_base import KnowledgeBase
        text = "A" * 400 + "\n\n" + "B" * 400
        chunks = KnowledgeBase.chunk_text(text, chunk_size=500)
        assert len(chunks) >= 2

    def test_empty_text_no_chunks(self):
        from agent.knowledge_base import KnowledgeBase
        chunks = KnowledgeBase.chunk_text("")
        assert len(chunks) == 0

    def test_single_paragraph_at_boundary(self):
        from agent.knowledge_base import KnowledgeBase
        text = "C" * 498
        chunks = KnowledgeBase.chunk_text(text, chunk_size=500)
        assert len(chunks) == 1


class TestKnowledgeBase:
    @pytest.fixture
    def kb(self, tmp_path):
        """Isolated ChromaDB with dummy embedding function."""
        import chromadb
        from chromadb.config import Settings

        ef = DummyEmbeddingFunction()
        client = chromadb.PersistentClient(
            path=str(tmp_path / "chroma_test"),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(
            name="audit_knowledge",
            embedding_function=ef,
        )

        # Build a KnowledgeBase manually with our test collection
        from agent.knowledge_base import KnowledgeBase
        kb = KnowledgeBase.__new__(KnowledgeBase)
        kb.persist_dir = str(tmp_path / "chroma_test")
        kb.chroma_client = client
        kb.collection = collection
        return kb

    def test_initial_count_is_zero(self, kb):
        assert kb.count() == 0

    def test_search_on_empty_returns_nothing(self, kb):
        results = kb.search("test query")
        assert results == []

    def test_ingest_and_search(self, kb):
        kb.ingest_rules([
            {"entity": "forbidden", "fact": "do not use 绝绝子"},
            {"entity": "format", "fact": "title uses Song font"},
        ])
        assert kb.count() == 2

        results = kb.search("绝绝子", top_k=2)
        assert len(results) >= 1
        assert any("绝绝子" in r for r in results)

    def test_ingest_document_chunks(self, kb):
        content = "A" * 400 + "\n\n" + "B" * 400
        count = kb.ingest_document("test.txt", content)
        assert count >= 2

    def test_clear_resets_count(self, kb):
        kb.ingest_rules([{"entity": "test", "fact": "a rule"}])
        assert kb.count() == 1
        kb.clear()
        assert kb.count() == 0
