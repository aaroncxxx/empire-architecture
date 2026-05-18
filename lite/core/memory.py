"""帝国架构 v2.9 - Agent 记忆系统"""
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from .logger import get_logger

log = get_logger("memory")

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "memory")
os.makedirs(MEMORY_DIR, exist_ok=True)


@dataclass
class MemoryEntry:
    """单条记忆"""
    content: str
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5   # 0~1
    tags: list = field(default_factory=list)
    task_id: str = ""


class AgentMemory:
    """v2.9: Agent 记忆系统 - 短期 + 长期"""

    def __init__(self, agent_id: str, short_term_size: int = 20,
                 long_term_file: str = ""):
        self.agent_id = agent_id
        # 短期记忆（滑动窗口）
        self.short_term: deque[MemoryEntry] = deque(maxlen=short_term_size)
        # 长期记忆（持久化文件）
        self._lt_file = long_term_file or os.path.join(
            MEMORY_DIR, f"{agent_id}.json"
        )
        self.long_term: list[MemoryEntry] = []
        self._load_long_term()

    def remember(self, content: str, importance: float = 0.5,
                 tags: list = None, task_id: str = ""):
        """记录一条记忆"""
        entry = MemoryEntry(
            content=content, importance=importance,
            tags=tags or [], task_id=task_id,
        )
        self.short_term.append(entry)

        # 高重要性自动存入长期记忆
        if importance >= 0.8:
            self.long_term.append(entry)
            self._save_long_term()
            log.debug(f"[{self.agent_id}] 长期记忆+1: {content[:50]}...")

    def recall_recent(self, n: int = 5) -> list[str]:
        """回忆最近 N 条"""
        return [m.content for m in list(self.short_term)[-n:]]

    def recall_important(self, n: int = 5) -> list[str]:
        """回忆最重要的 N 条"""
        sorted_mem = sorted(self.long_term, key=lambda m: m.importance, reverse=True)
        return [m.content for m in sorted_mem[:n]]

    def recall_by_tag(self, tag: str) -> list[str]:
        """按标签回忆"""
        results = []
        for m in self.short_term:
            if tag in m.tags:
                results.append(m.content)
        for m in self.long_term:
            if tag in m.tags and m.content not in results:
                results.append(m.content)
        return results

    def get_context_window(self, max_chars: int = 2000) -> str:
        """获取记忆上下文窗口（用于注入 prompt）"""
        lines = []
        total = 0

        # 先加重要的长期记忆
        for m in sorted(self.long_term, key=lambda x: x.importance, reverse=True):
            if total + len(m.content) > max_chars:
                break
            lines.append(f"[经验] {m.content}")
            total += len(m.content)

        # 再加最近的短期记忆
        for m in reversed(list(self.short_term)):
            if total + len(m.content) > max_chars:
                break
            lines.append(f"[近期] {m.content}")
            total += len(m.content)

        return "\n".join(reversed(lines))

    def _load_long_term(self):
        if os.path.exists(self._lt_file):
            try:
                with open(self._lt_file, encoding="utf-8") as f:
                    data = json.load(f)
                self.long_term = [
                    MemoryEntry(**e) for e in data
                ]
            except Exception:
                self.long_term = []

    def _save_long_term(self):
        try:
            data = [
                {"content": m.content, "timestamp": m.timestamp,
                 "importance": m.importance, "tags": m.tags, "task_id": m.task_id}
                for m in self.long_term[-100:]  # 最多保留 100 条
            ]
            with open(self._lt_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"保存长期记忆失败: {e}")

    def get_stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "short_term": len(self.short_term),
            "long_term": len(self.long_term),
        }
