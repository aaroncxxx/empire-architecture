"""帝国架构 v2.9 - 锦衣卫安全系统（增强版）"""
import time
import asyncio
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .logger import get_logger

log = get_logger("security")


class ViolationLevel(Enum):
    LEVEL1 = 1
    LEVEL2 = 2
    LEVEL3 = 3


@dataclass
class Violation:
    agent_id: str
    level: ViolationLevel
    description: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    votes: dict = field(default_factory=dict)


# v2.9: 敏感操作类型
SENSITIVE_KEYWORDS = [
    "发送到外部", "API调用", "网络请求", "删除", "修改配置",
    "访问密钥", "导出数据", "外部接口", "http", "curl", "wget",
]


class SecuritySystem:
    """锦衣卫安全系统 v2.9 - 事前审批 + 事后审计 + 自动升级"""

    def __init__(self):
        self.violations: deque[Violation] = deque(maxlen=500)
        self.warning_counts: dict[str, int] = {}
        self._pending_approvals: dict[str, asyncio.Future] = {}
        # v2.9: 安全事件统计
        self.event_stats = {"blocked": 0, "approved": 0, "violations": 0}

    def check_sensitive(self, task_content: str) -> tuple[bool, list[str]]:
        """v2.9: 检查任务是否包含敏感操作"""
        triggered = []
        for kw in SENSITIVE_KEYWORDS:
            if kw in task_content.lower():
                triggered.append(kw)
        return bool(triggered), triggered

    def report_violation(self, agent_id: str, level: ViolationLevel,
                         description: str) -> Violation:
        v = Violation(agent_id=agent_id, level=level, description=description)
        self.violations.append(v)
        self.event_stats["violations"] += 1
        log.warning(f"违规 [{level.name}] {agent_id}: {description}")
        return v

    def vote(self, violation_idx: int, voter_id: str, approve: bool):
        if 0 <= violation_idx < len(self.violations):
            self.violations[violation_idx].votes[voter_id] = approve

    def get_vote_result(self, violation_idx: int) -> Optional[bool]:
        v = self.violations[violation_idx]
        if not v.votes:
            return None
        yes = sum(1 for x in v.votes.values() if x)
        return yes > len(v.votes) / 2

    def add_warning(self, agent_id: str):
        self.warning_counts[agent_id] = self.warning_counts.get(agent_id, 0) + 1
        if self.warning_counts[agent_id] >= 3:
            log.error(f"Agent {agent_id} 累计 3 次警告，建议升级处理")

    def get_pending_violations(self) -> list:
        return [v for v in self.violations if not v.resolved]

    def get_status(self) -> dict:
        pending = len([v for v in self.violations if not v.resolved])
        return {
            "total_violations": len(self.violations),
            "pending": pending,
            "warnings": dict(self.warning_counts),
            **self.event_stats,
        }
