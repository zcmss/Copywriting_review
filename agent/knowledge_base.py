# agent/knowledge_base.py
"""RAG knowledge base -- ChromaDB-backed semantic memory engine.

Uses ChromaDB's built-in ONNX embedding model (all-MiniLM-L6-v2)
stored locally inside the project directory. No external API needed.
"""
import os
import hashlib
import re
from typing import List, Dict

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
from rank_bm25 import BM25Okapi  # 需要 pip install rank_bm25

# 保持你的优秀设计：本地沙箱化模型
_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_models")
os.makedirs(_MODEL_DIR, exist_ok=True)
ONNXMiniLM_L6_V2.DOWNLOAD_PATH = os.path.join(_MODEL_DIR, "all-MiniLM-L6-v2")

_default_ef = ONNXMiniLM_L6_V2()


class KnowledgeBase:
    """强化版：支持混合检索（Semantic + Keyword）与健壮切块的知识库"""

    def __init__(self, persist_dir="agent/chroma_db"):
        self.persist_dir = persist_dir
        self.chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="audit_knowledge",
            embedding_function=_default_ef,
            metadata={"description": "audit rules and compliance knowledge"},
        )

        # 本地内存 BM25 语料库，用于关键词补充
        self.bm25_corpus = []
        self.bm25_metadata = []
        self.bm25 = None
        self._rebuild_bm25_from_chroma()  # 启动时从 Chroma 恢复 BM25 状态

    def _tokenize(self, text: str) -> List[str]:
        """专门应对审计黑话和单号的极简中文/英文分词（按字/词块）"""
        # 将文本转化为小写，并切分成单个字符/英文单词，确保 'yyds' 或特定违禁词能被精确击中
        return [token.lower() for token in re.findall(r'\w+|\S', text) if token.strip()]

    def _rebuild_bm25_from_chroma(self):
        """核心改进：启动时从本地 Chroma 中把文本捞出来同步进 BM25，保持两边一致"""
        count = self.collection.count()
        if count == 0:
            return

        # 捞出全部持久化的数据
        all_data = self.collection.get(include=["documents", "metadatas"])
        if all_data and all_data["documents"]:
            for doc, meta in zip(all_data["documents"], all_data["metadatas"]):
                self.bm25_corpus.append(self._tokenize(doc))
                self.bm25_metadata.append({"text": doc, "meta": meta})
            self.bm25 = BM25Okapi(self.bm25_corpus)

    # ===== 健壮的带 Overlap 切块 =====

    @staticmethod
    def chunk_text(text, chunk_size=500, overlap=100):
        """改进版切块：按字符大小滑动切块，彻底杜绝无换行长文本导致的死循环漏洞"""
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        idx = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk_content = text[start:end].strip()

            if chunk_content:
                chunks.append({
                    "text": chunk_content,
                    "index": idx,
                    "chunk_id": f"chunk_{idx}",
                })
                idx += 1

            # 指针向前移动（保持 overlap 交叉）
            start += (chunk_size - overlap)
            if start >= text_len or chunk_size <= overlap:
                break

        return chunks

    # ===== 写入与幂等性改进 =====

    def ingest_rules(self, rules):
        """批量更新/插入审计规则（使用 upsert 保持幂等性）"""
        texts = []
        ids = []
        metadatas = []

        for rule in rules:
            entity = rule.get("entity", "uncategorized")
            fact = rule.get("fact", "")
            full_text = f"[{entity}] {fact}"

            # 生成确定性的 MD5 ID
            doc_id = hashlib.md5(full_text.encode()).hexdigest()[:16]
            texts.append(full_text)
            ids.append(doc_id)
            metadatas.append({"entity": entity, "type": "rule"})

            # 同步更新本地内存 BM25
            tokenized = self._tokenize(full_text)
            self.bm25_corpus.append(tokenized)
            self.bm25_metadata.append({"text": full_text, "meta": metadatas[-1]})

        if texts:
            # 改进点：用 upsert 代替 add，防止重复执行脚本时崩溃
            self.collection.upsert(documents=texts, ids=ids, metadatas=metadatas)
            self.bm25 = BM25Okapi(self.bm25_corpus)

    def ingest_document(self, file_path, content):
        """安全的将文档切块并灌入双路索引"""
        chunks = self.chunk_text(content, chunk_size=500, overlap=100)
        if not chunks:
            return 0
 
        texts = [c["text"] for c in chunks]
        ids = [f"{file_path}#{c['chunk_id']}" for c in chunks]
        metadatas = [
            {"source": file_path, "chunk_index": c["index"], "type": "document"}
            for c in chunks
        ]

        # 写入 Chroma
        self.collection.upsert(documents=texts, ids=ids, metadatas=metadatas)

        # 同步增量写入 BM25
        for text, meta in zip(texts, metadatas):
            self.bm25_corpus.append(self._tokenize(text))
            self.bm25_metadata.append({"text": text, "meta": meta})

        self.bm25 = BM25Okapi(self.bm25_corpus)
        return len(chunks)

    # ===== 核心飞跃：真正的混合检索 =====

    def search(self, query, top_k=5):
        """混合检索（Semantic Vector + BM25 Keyword）联合召回"""
        if self.collection.count() == 0:
            return []

        # 用字典实现天然的去重
        deduped_results = {}

        # 第一路：Chroma 语义向量检索
        chroma_top_k = min(top_k, self.collection.count())
        semantic_results = self.collection.query(
            query_texts=[query],
            n_results=chroma_top_k,
        )

        if semantic_results and semantic_results.get("documents"):
            for doc in semantic_results["documents"][0]:
                deduped_results[doc] = True

        # 第二路：BM25 精准关键词捞网（捕获违禁词、单号、否定词）
        if self.bm25:
            tokenized_query = self._tokenize(query)
            scores = self.bm25.get_scores(tokenized_query)
            # 捞出得分最高的前 top_k 个索引
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

            for idx in top_indices:
                if scores[idx] > 0:  # 只有真正匹配到关键词的才召回
                    matched_text = self.bm25_metadata[idx]["text"]
                    deduped_results[matched_text] = True

        # 返回合并去重后的前 top_k 条文本结果
        return list(deduped_results.keys())[:top_k]

    # ===== admin =====

    def count(self):
        return self.collection.count()

    def clear(self):
        """重置两边的数据状态"""
        try:
            self.chroma_client.delete_collection("audit_knowledge")
        except Exception:
            pass
        self.collection = self.chroma_client.get_or_create_collection(
            name="audit_knowledge",
            embedding_function=_default_ef,
        )
        self.bm25_corpus = []
        self.bm25_metadata = []
        self.bm25 = None


# 全局单例
kb = KnowledgeBase()