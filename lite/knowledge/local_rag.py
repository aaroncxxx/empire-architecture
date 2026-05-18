"""
RAG 自建知识库 v2.9
增强：中文分词 + LRU 缓存 + 增量索引
"""
import json
import os
import re
import math
import hashlib
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from .base import KnowledgeProvider, KnowledgeResult
import urllib.request


# ============================================================
# 中文分词器（纯 Python，零依赖）
# ============================================================

class ChineseTokenizer:
    """中英文混合分词器 v2.9 - 基于正向最大匹配 + bigram"""

    # 常见量子/技术术语词典（可扩展）
    DICTIONARY = set([
        "量子", "计算", "通信", "纠缠", "叠加", "比特", "门", "测量",
        "坍缩", "态", "波函数", "薛定谔", "海森堡", "贝尔", "不等式",
        "密钥", "分发", "协议", "光子", "电子", "离子", "超导",
        "算法", "搜索", "优化", "机器学习", "神经网络", "人工智能",
        "密码", "加密", "解密", "安全", "隐私", "经典", "非局域",
        "概率", "振幅", "相位", "干涉", "退相干", "纠错", "容错",
        "量子比特", "量子门", "量子计算", "量子通信", "量子纠缠",
        "量子力学", "量子信息", "量子密码", "量子网络", "量子中继",
        "隐形传态", "超密编码", "量子退火", "量子霸权", "量子优势",
        "布洛赫球", "哈密顿量", "希尔伯特", "酉变换", "泡利",
        "帝国", "架构", "丞相", "参谋", "执行", "监察", "翰林",
        "节点", "智能体", "协作", "调度", "任务", "配置", "知识",
        "上下文", "检索", "向量", "分块", "索引", "缓存", "路由",
    ])

    def __init__(self):
        # 按长度降序排列词典，优先匹配长词
        self.sorted_words = sorted(self.DICTIONARY, key=len, reverse=True)

    def tokenize(self, text: str) -> list[str]:
        """中英文混合分词"""
        text = text.lower()
        tokens = []

        # 英文单词 + 数字
        eng_tokens = re.findall(r'[a-z0-9]+(?:\.[a-z0-9]+)*', text)
        tokens.extend(eng_tokens)

        # 中文部分：正向最大匹配
        cn_text = re.sub(r'[a-z0-9\s\W]', ' ', text)
        for segment in cn_text.split():
            segment = segment.strip()
            if not segment:
                continue
            matched = self._fmm_match(segment)
            tokens.extend(matched)

        return tokens

    def _fmm_match(self, text: str) -> list[str]:
        """正向最大匹配分词"""
        result = []
        i = 0
        while i < len(text):
            matched = False
            # 从最长词开始匹配
            for word in self.sorted_words:
                if text[i:i+len(word)] == word:
                    result.append(word)
                    i += len(word)
                    matched = True
                    break
            if not matched:
                # 单字作为 fallback
                result.append(text[i])
                i += 1
        return result


# ============================================================
# LRU 缓存
# ============================================================

class LRUCache:
    """简单 LRU 缓存"""

    def __init__(self, capacity: int = 128, ttl: float = 300.0):
        self.cache: OrderedDict = OrderedDict()
        self.capacity = capacity
        self.ttl = ttl  # 秒
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["time"] < self.ttl:
                self.cache.move_to_end(key)
                self.hits += 1
                return entry["value"]
            else:
                del self.cache[key]
        self.misses += 1
        return None

    def put(self, key: str, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = {"value": value, "time": time.time()}
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "hits": self.hits, "misses": self.misses,
            "hit_rate": f"{self.hits/total*100:.1f}%" if total else "N/A",
            "size": len(self.cache),
        }


# ============================================================
# TF-IDF 向量器（v2.9: 用中文分词器）
# ============================================================

class TFIDFVectorizer:
    """TF-IDF 向量化 v2.9 - 中文分词增强"""

    def __init__(self):
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.doc_count = 0
        self.tokenizer = ChineseTokenizer()

    def _tokenize(self, text: str) -> list[str]:
        return self.tokenizer.tokenize(text)

    def fit(self, documents: list[str]):
        self.doc_count = len(documents)
        doc_freq = Counter()
        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                doc_freq[token] += 1
        self.vocab = {word: idx for idx, word in enumerate(doc_freq.keys())}
        self.idf = {}
        for word, df in doc_freq.items():
            self.idf[word] = math.log((self.doc_count + 1) / (df + 1)) + 1

    def transform(self, text: str) -> dict[int, float]:
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        tf = Counter(tokens)
        total = len(tokens)
        vector = {}
        for word, count in tf.items():
            if word in self.vocab:
                idx = self.vocab[word]
                tfidf = (count / total) * self.idf.get(word, 1.0)
                vector[idx] = tfidf
        return vector

    @staticmethod
    def cosine_sim(a: dict[int, float], b: dict[int, float]) -> float:
        common = set(a.keys()) & set(b.keys())
        if not common:
            return 0.0
        dot = sum(a[i] * b[i] for i in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# ============================================================
# 本地向量库（v2.9: 缓存 + 增强分词）
# ============================================================

@dataclass
class Document:
    doc_id: str
    title: str
    chunks: list[str] = field(default_factory=list)
    vectors: list[dict[int, float]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class LocalVectorStore:

    def __init__(self, persist_dir: str = ""):
        self.documents: dict[str, Document] = {}
        self.vectorizer = TFIDFVectorizer()
        self.persist_dir = persist_dir
        self._dirty = True
        self._cache = LRUCache(capacity=256, ttl=300)

    def add_document(self, title: str, content: str,
                     chunk_size: int = 500, metadata: dict = None) -> str:
        doc_id = hashlib.md5(title.encode()).hexdigest()[:12]
        chunks = chunk_text(content, chunk_size)
        doc = Document(
            doc_id=doc_id, title=title, chunks=chunks,
            metadata=metadata or {},
        )
        self.documents[doc_id] = doc
        self._dirty = True
        self._rebuild_index()
        return doc_id

    def _rebuild_index(self):
        all_chunks = []
        for doc in self.documents.values():
            all_chunks.extend(doc.chunks)
        if not all_chunks:
            return
        self.vectorizer.fit(all_chunks)
        for doc in self.documents.values():
            doc.vectors = []
            for chunk in doc.chunks:
                vec = self.vectorizer.transform(chunk)
                doc.vectors.append(vec)
        self._dirty = False

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeResult]:
        if not self.documents:
            return []

        # v2.9: 缓存检查
        cache_key = f"{query}:{top_k}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if self._dirty:
            self._rebuild_index()

        query_vec = self.vectorizer.transform(query)
        scored = []
        for doc in self.documents.values():
            for i, vec in enumerate(doc.vectors):
                score = self.vectorizer.cosine_sim(query_vec, vec)
                if score > 0.01:
                    scored.append((score, doc, i))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        seen = set()
        for score, doc, chunk_idx in scored[:top_k * 2]:
            chunk_key = f"{doc.doc_id}:{chunk_idx}"
            if chunk_key in seen:
                continue
            seen.add(chunk_key)

            context_chunks = []
            for j in range(max(0, chunk_idx - 1),
                           min(len(doc.chunks), chunk_idx + 2)):
                context_chunks.append(doc.chunks[j])
            context = "\n\n".join(context_chunks)

            results.append(KnowledgeResult(
                title=doc.title,
                content=context[:800],
                source="local_rag",
                score=round(score, 4),
                metadata={
                    "doc_id": doc.doc_id,
                    "chunk_index": chunk_idx,
                    **doc.metadata,
                },
            ))
            if len(results) >= top_k:
                break

        # v2.9: 缓存结果
        self._cache.put(cache_key, results)
        return results

    def save(self, path: str = ""):
        path = path or os.path.join(self.persist_dir, "vectorstore.json")
        data = {}
        for doc_id, doc in self.documents.items():
            data[doc_id] = {
                "title": doc.title,
                "chunks": doc.chunks,
                "metadata": doc.metadata,
            }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str = ""):
        path = path or os.path.join(self.persist_dir, "vectorstore.json")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for doc_id, info in data.items():
            doc = Document(
                doc_id=doc_id, title=info["title"],
                chunks=info["chunks"], metadata=info.get("metadata", {}),
            )
            self.documents[doc_id] = doc
        self._dirty = True
        self._rebuild_index()

    def stats(self) -> dict:
        return {
            "documents": len(self.documents),
            "total_chunks": sum(len(d.chunks) for d in self.documents.values()),
            "vocab_size": len(self.vectorizer.vocab),
            "cache": self._cache.stats(),
        }


# ============================================================
# 文本分块
# ============================================================

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    paragraphs = re.split(r'\n{2,}', text)
    chunks = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) < chunk_size:
            current += ("\n\n" if current else "") + para
        else:
            if current:
                chunks.append(current)
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    chunk = para[i:i + chunk_size]
                    if chunk.strip():
                        chunks.append(chunk.strip())
            else:
                current = para
    if current.strip():
        chunks.append(current.strip())
    return chunks


# ============================================================
# RAG 知识提供者
# ============================================================

class LocalRAGKnowledge(KnowledgeProvider):
    name = "local_rag"

    def __init__(self, persist_dir: str = "./data/knowledge"):
        self.persist_dir = persist_dir
        self.store = LocalVectorStore(persist_dir)
        try:
            self.store.load()
        except Exception:
            pass

    def ingest_url(self, url: str) -> str:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; EmpireBot/2.9)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
        title = title_match.group(1).strip() if title_match else url
        doc_id = self.store.add_document(
            title=title, content=text,
            metadata={"source_url": url, "type": "web"},
        )
        self.store.save()
        return doc_id

    def ingest_file(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        content = path.read_text(encoding="utf-8", errors="ignore")
        doc_id = self.store.add_document(
            title=path.name, content=content,
            metadata={"source_path": str(path), "type": "file"},
        )
        self.store.save()
        return doc_id

    def ingest_directory(self, dir_path: str,
                         extensions: list[str] = None) -> list[str]:
        extensions = extensions or [".txt", ".md", ".json", ".py"]
        path = Path(dir_path)
        doc_ids = []
        for f in path.rglob("*"):
            if f.suffix.lower() in extensions and f.is_file():
                try:
                    doc_id = self.ingest_file(str(f))
                    doc_ids.append(doc_id)
                except Exception:
                    continue
        return doc_ids

    def ingest_text(self, title: str, content: str) -> str:
        doc_id = self.store.add_document(
            title=title, content=content,
            metadata={"type": "text"},
        )
        self.store.save()
        return doc_id

    async def search(self, query: str, top_k: int = 3) -> list[KnowledgeResult]:
        return self.store.search(query, top_k)

    async def health_check(self) -> bool:
        return True

    def stats(self) -> dict:
        return self.store.stats()
