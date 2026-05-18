"""帝国架构 v2.9 - 任务队列（优先级 + 重试 + 超时 + 熔断）"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum
from .logger import get_logger

log = get_logger("taskqueue")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class Task:
    task_id: str
    agent_id: str
    prompt: str
    priority: int = 5        # 1=最高
    max_retries: int = 2
    timeout_seconds: float = 60.0
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    completed_at: float = 0

    def __lt__(self, other):
        return self.priority < other.priority


class CircuitBreaker:
    """熔断器：连续失败 N 次后暂时停止调度"""

    def __init__(self, threshold: int = 5, reset_timeout: float = 300.0):
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failures: dict[str, int] = {}
        self.opened_at: dict[str, float] = {}

    def record_failure(self, agent_id: str):
        self.failures[agent_id] = self.failures.get(agent_id, 0) + 1
        if self.failures[agent_id] >= self.threshold:
            self.opened_at[agent_id] = time.time()
            log.warning(f"熔断器开启: {agent_id} (连续 {self.failures[agent_id]} 次失败)")

    def record_success(self, agent_id: str):
        self.failures[agent_id] = 0
        self.opened_at.pop(agent_id, None)

    def is_open(self, agent_id: str) -> bool:
        if agent_id not in self.opened_at:
            return False
        elapsed = time.time() - self.opened_at[agent_id]
        if elapsed > self.reset_timeout:
            # 半开状态，允许重试
            del self.opened_at[agent_id]
            self.failures[agent_id] = 0
            log.info(f"熔断器半开: {agent_id}，允许重试")
            return False
        return True


class TaskQueue:
    """v2.9: 优先级任务队列 + 重试 + 超时 + 熔断"""

    def __init__(self, max_concurrent: int = 16):
        self.queue = asyncio.PriorityQueue()
        self.results: dict[str, Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.breaker = CircuitBreaker()
        self._running = False
        self.stats = {"submitted": 0, "completed": 0, "failed": 0, "retried": 0}

    async def submit(self, task: Task):
        """提交任务"""
        self.stats["submitted"] += 1
        self.results[task.task_id] = task
        await self.queue.put(task)

    async def execute(self, task: Task, handler: Callable) -> Task:
        """执行单个任务（带重试 + 超时）"""
        # 熔断检查
        if self.breaker.is_open(task.agent_id):
            task.status = TaskStatus.CIRCUIT_OPEN
            task.error = f"熔断器开启，{task.agent_id} 暂不可用"
            return task

        async with self.semaphore:
            for attempt in range(task.max_retries + 1):
                task.attempts = attempt + 1
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()

                try:
                    result = await asyncio.wait_for(
                        handler(task), timeout=task.timeout_seconds
                    )
                    task.result = result
                    task.status = TaskStatus.SUCCESS
                    task.completed_at = time.time()
                    self.breaker.record_success(task.agent_id)
                    self.stats["completed"] += 1
                    log.info(f"任务完成: {task.task_id} ({task.completed_at - task.started_at:.1f}s)")
                    return task

                except asyncio.TimeoutError:
                    task.status = TaskStatus.TIMEOUT
                    task.error = f"超时 ({task.timeout_seconds}s)"
                    self.breaker.record_failure(task.agent_id)
                    log.warning(f"任务超时: {task.task_id} 第{attempt+1}次")

                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    self.breaker.record_failure(task.agent_id)
                    log.error(f"任务失败: {task.task_id} 第{attempt+1}次: {e}")

                # 重试
                if attempt < task.max_retries:
                    task.status = TaskStatus.RETRYING
                    self.stats["retried"] += 1
                    await asyncio.sleep(1.0 * (attempt + 1))  # 指数退避

            self.stats["failed"] += 1
            return task

    def get_result(self, task_id: str) -> Optional[Task]:
        return self.results.get(task_id)

    def get_stats(self) -> dict:
        return {
            **self.stats,
            "queue_size": self.queue.qsize(),
            "circuit_open": [aid for aid in self.breaker.opened_at],
        }
