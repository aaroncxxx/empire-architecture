"""帝国架构 v2.9 - 消息总线（增强版）"""
import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from .logger import get_logger

log = get_logger("bus")


class MessageType(Enum):
    COMMAND = "command"
    TASK = "task"
    RESULT = "result"
    REPORT = "report"
    ALERT = "alert"
    VOTE = "vote"
    SYNC = "sync"
    HEARTBEAT = "heartbeat"
    DIRECT = "direct"          # Agent 间直接通信（v2.9）
    APPROVAL = "approval"      # 事前审批（v2.9）


@dataclass
class Message:
    msg_type: MessageType
    sender: str
    receiver: str
    content: str
    task_id: Optional[str] = None
    priority: int = 5
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["msg_type"] = self.msg_type.value
        return d

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)


class MessageBus:
    """异步消息总线 v2.9 - 带内存限制、Agent间通信、统计"""

    def __init__(self, max_history: int = 2000):
        self.queues: dict[str, asyncio.PriorityQueue] = {}
        self.history: deque[Message] = deque(maxlen=max_history)
        self._subscribers: dict[str, list] = {}
        # v2.9: 统计
        self.stats = {"sent": 0, "received": 0, "dropped": 0}

    def register(self, agent_id: str):
        if agent_id not in self.queues:
            self.queues[agent_id] = asyncio.PriorityQueue()

    async def send(self, msg: Message):
        """发送消息"""
        self.history.append(msg)
        self.stats["sent"] += 1
        if msg.receiver in self.queues:
            await self.queues[msg.receiver].put((msg.priority, msg.timestamp, msg))
        # 广播给订阅者
        for sub_id in self._subscribers.get(msg.msg_type.value, []):
            if sub_id in self.queues and sub_id != msg.receiver:
                await self.queues[sub_id].put((msg.priority, msg.timestamp, msg))

    async def send_direct(self, sender: str, receiver: str, content: str,
                          task_id: str = ""):
        """v2.9: Agent 间直接通信"""
        msg = Message(
            msg_type=MessageType.DIRECT,
            sender=sender, receiver=receiver,
            content=content, task_id=task_id,
        )
        await self.send(msg)
        log.debug(f"直接消息: {sender} → {receiver}")

    async def receive(self, agent_id: str, timeout: float = 30) -> Optional[Message]:
        """接收消息"""
        if agent_id not in self.queues:
            return None
        try:
            _, _, msg = await asyncio.wait_for(
                self.queues[agent_id].get(), timeout=timeout
            )
            self.stats["received"] += 1
            return msg
        except asyncio.TimeoutError:
            return None

    def subscribe(self, agent_id: str, msg_type: str):
        self._subscribers.setdefault(msg_type, []).append(agent_id)

    def get_history(self, limit: int = 50) -> list[Message]:
        return list(self.history)[-limit:]

    def get_stats(self) -> dict:
        return {**self.stats, "queue_depth": {
            aid: q.qsize() for aid, q in self.queues.items() if not q.empty()
        }}
