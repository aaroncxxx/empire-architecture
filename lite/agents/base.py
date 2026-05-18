"""帝国架构 v2.9 - Agent 基类（全面增强）"""
import asyncio
import json
import time
import uuid
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional
from collections import deque
from core.bus import MessageBus, Message, MessageType
from core.tokens import TokenTracker
from core.config import load_llm_credentials, load_empire_config
from core.model_router import select_model
from core.memory import AgentMemory
from core.logger import get_logger

log = get_logger("agent")


@dataclass
class AgentState:
    agent_id: str
    name: str
    role: str
    tags: list = field(default_factory=list)     # v2.9: 标签系统
    status: str = "idle"
    current_task: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0                         # v2.9
    avg_response_time: float = 0.0                # v2.9
    uptime_start: float = field(default_factory=time.time)


class Agent:
    """Agent 基类 v2.9 - 记忆 + 模型路由 + 标签 + 评分 + 对话历史"""

    def __init__(self, agent_id: str, name: str, role: str,
                 system_prompt: str, bus: MessageBus, tracker: TokenTracker,
                 tags: list = None):
        self.state = AgentState(
            agent_id=agent_id, name=name, role=role, tags=tags or []
        )
        self.system_prompt = system_prompt
        self.bus = bus
        self.tracker = tracker
        self.bus.register(agent_id)
        self._credentials = None
        self._config = None
        # v2.9: 记忆 + 对话历史 + 评分
        self.memory = AgentMemory(agent_id)
        self.conversation_history: deque[dict] = deque(maxlen=10)
        self.performance_score: float = 1.0
        self._response_times: deque[float] = deque(maxlen=20)

    def _get_credentials(self):
        if self._credentials is None:
            self._credentials = load_llm_credentials()
            self._config = load_empire_config()
        return self._credentials, self._config

    async def call_llm(self, prompt: str, context: str = "") -> str:
        """调用 LLM（v2.9: 模型路由 + 记忆注入 + 对话历史）"""
        creds, cfg = self._get_credentials()
        if not creds:
            return "[ERROR] 无可用的 LLM 凭据"

        if not self.tracker.check_budget(self.state.agent_id):
            return "[ERROR] Token 额度已用完"

        # v2.9: 模型路由
        model_info = select_model(self.state.role, prompt)
        model_name = model_info["name"]
        max_tokens = model_info["max_tokens"]
        temperature = model_info["temperature"]

        # v2.9: 记忆上下文注入
        memory_ctx = self.memory.get_context_window(max_chars=1500)

        messages = [{"role": "system", "content": self.system_prompt}]

        # 注入记忆
        if memory_ctx:
            messages.append({
                "role": "system",
                "content": f"你的近期经验和记忆（仅供参考）：\n{memory_ctx}"
            })

        # 注入知识上下文
        if context:
            messages.append({
                "role": "user",
                "content": f"背景知识（仅供参考，基于检索自动注入）：\n{context}"
            })

        # v2.9: 注入对话历史
        for hist in list(self.conversation_history)[-4:]:
            messages.append(hist)

        messages.append({"role": "user", "content": prompt})

        body = json.dumps({
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds['api_key']}",
        }

        url = creds['base_url']
        if not url.endswith("/chat/completions"):
            url = url.rstrip("/") + "/chat/completions"

        start_time = time.time()

        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=cfg["llm"]["timeout_seconds"]) as resp:
                data = json.loads(resp.read())

            elapsed = time.time() - start_time
            self._response_times.append(elapsed)

            usage = data.get("usage", {})
            self.tracker.log_usage(
                self.state.agent_id,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                model=model_name,
            )

            content = data["choices"][0]["message"]["content"]
            self.state.tasks_completed += 1

            # v2.9: 更新对话历史
            self.conversation_history.append({"role": "user", "content": prompt[:500]})
            self.conversation_history.append({"role": "assistant", "content": content[:500]})

            # v2.9: 记住这次任务
            self.memory.remember(
                f"任务: {prompt[:100]}... → 成功",
                importance=0.3, tags=["task", "success"],
            )

            # v2.9: 更新平均响应时间
            if self._response_times:
                self.state.avg_response_time = sum(self._response_times) / len(self._response_times)

            return content

        except urllib.error.HTTPError as e:
            self.state.tasks_failed += 1
            self.memory.remember(f"任务失败: HTTP {e.code}", importance=0.6, tags=["error"])
            return f"[ERROR] API 调用失败: {e.code} {e.reason}"
        except Exception as e:
            self.state.tasks_failed += 1
            self.memory.remember(f"任务失败: {e}", importance=0.6, tags=["error"])
            return f"[ERROR] {str(e)}"

    async def process_task(self, task_id: str, prompt: str, context: str = "") -> str:
        """处理任务"""
        self.state.status = "busy"
        self.state.current_task = task_id
        try:
            result = await self.call_llm(prompt, context)
            self.state.status = "idle"
            self.state.current_task = ""
            return result
        except Exception as e:
            self.state.status = "error"
            return f"[ERROR] {self.state.name} 处理失败: {e}"

    def get_status(self) -> dict:
        return {
            "id": self.state.agent_id,
            "name": self.state.name,
            "role": self.state.role,
            "tags": self.state.tags,
            "status": self.state.status,
            "current_task": self.state.current_task,
            "tasks_completed": self.state.tasks_completed,
            "tasks_failed": self.state.tasks_failed,
            "avg_response_time": round(self.state.avg_response_time, 2),
            "performance_score": round(self.performance_score, 2),
            "memory": self.memory.get_stats(),
            "uptime": round(time.time() - self.state.uptime_start, 0),
        }
