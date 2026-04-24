"""帝国架构 - Agent 基类 (v1.6)"""
import asyncio
import json
import time
import uuid
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, Callable
from core.bus import MessageBus, Message, MessageType
from core.tokens import TokenTracker
from core.config import load_llm_credentials, load_empire_config


@dataclass
class AgentState:
    agent_id: str
    name: str
    role: str
    status: str = "idle"       # idle, busy, error, terminated
    current_task: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0
    uptime_start: float = field(default_factory=time.time)
    # v1.6: 能力标签（柔性角色）
    capabilities: list = field(default_factory=list)
    assist_roles: list = field(default_factory=list)


DEFAULT_RETRY = 2          # 默认重试次数
DEFAULT_TIMEOUT = 30       # 默认单节点超时(秒)
DEFAULT_TASK_TIMEOUT = 60  # 默认任务超时(秒)


class Agent:
    """Agent 基类 (v1.6)

    新增特性:
    - 节点超时 + 失败重试
    - 消息总线 peer-to-peer 通信
    - 柔性角色能力标签
    - 知识检索便捷方法
    """

    def __init__(self, agent_id: str, name: str, role: str,
                 system_prompt: str, bus: MessageBus, tracker: TokenTracker,
                 capabilities: list = None, assist_roles: list = None):
        self.state = AgentState(
            agent_id=agent_id, name=name, role=role,
            capabilities=capabilities or [],
            assist_roles=assist_roles or [],
        )
        self.system_prompt = system_prompt
        self.bus = bus
        self.tracker = tracker
        self.bus.register(agent_id)
        self._credentials = None
        self._config = None
        # v1.6: 知识路由器引用（由 mount_knowledge 注入）
        self.knowledge_router = None

    def _get_credentials(self):
        if self._credentials is None:
            self._credentials = load_llm_credentials()
            self._config = load_empire_config()
        return self._credentials, self._config

    # ───────────────────── LLM 调用（带重试） ─────────────────────

    async def call_llm(self, prompt: str, context: str = "",
                       retries: int = DEFAULT_RETRY,
                       timeout: float = DEFAULT_TIMEOUT) -> str:
        """调用 LLM — 带超时 + 重试"""
        creds, cfg = self._get_credentials()
        if not creds:
            return "[ERROR] 无可用的 LLM 凭据"

        if not self.tracker.check_budget(self.state.agent_id):
            return "[ERROR] Token 额度已用完"

        messages = [{"role": "system", "content": self.system_prompt}]
        if context:
            messages.append({"role": "user", "content": f"背景信息：\n{context}"})
        messages.append({"role": "user", "content": prompt})

        body = json.dumps({
            "model": cfg["llm"]["model"],
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds['api_key']}",
        }

        url = creds['base_url']
        if not url.endswith("/chat/completions"):
            url = url.rstrip("/") + "/chat/completions"

        last_error = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=headers)
                loop = asyncio.get_event_loop()
                data = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: json.loads(
                            urllib.request.urlopen(req, timeout=timeout).read()
                        ),
                    ),
                    timeout=timeout + 5,
                )

                usage = data.get("usage", {})
                self.tracker.log_usage(
                    self.state.agent_id,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    model=cfg["llm"]["model"],
                )

                content = data["choices"][0]["message"]["content"]
                self.state.tasks_completed += 1
                return content

            except (asyncio.TimeoutError, urllib.error.URLError, Exception) as e:
                last_error = e
                if attempt < retries:
                    wait = 1.0 * (attempt + 1)  # 线性退避
                    await asyncio.sleep(wait)
                    continue

        self.state.tasks_failed += 1
        return f"[ERROR] {self.state.name} LLM 调用失败（重试 {retries} 次）: {last_error}"

    # ───────────────────── 任务处理（带超时） ─────────────────────

    async def process_task(self, task_id: str, prompt: str,
                           context: str = "",
                           timeout: float = DEFAULT_TASK_TIMEOUT) -> str:
        """处理任务 — 带整体超时"""
        self.state.status = "busy"
        self.state.current_task = task_id
        try:
            result = await asyncio.wait_for(
                self.call_llm(prompt, context),
                timeout=timeout,
            )
            self.state.status = "idle"
            self.state.current_task = ""
            return result
        except asyncio.TimeoutError:
            self.state.status = "error"
            self.state.tasks_failed += 1
            return f"[TIMEOUT] {self.state.name} 任务超时（{timeout}s）"
        except Exception as e:
            self.state.status = "error"
            self.state.tasks_failed += 1
            return f"[ERROR] {self.state.name} 处理失败: {e}"

    # ───────────────────── Peer-to-Peer 通信 ─────────────────────

    async def send_to_peer(self, target_id: str, content: str,
                           task_id: str = "", priority: int = 5) -> None:
        """向另一个 Agent 发送消息（peer-to-peer，单向）"""
        msg = Message(
            msg_type=MessageType.SYNC,
            sender=self.state.agent_id,
            receiver=target_id,
            content=content,
            task_id=task_id,
            priority=priority,
        )
        await self.bus.send(msg)

    async def request_from_peer(self, target_id: str, prompt: str,
                                task_id: str = "", timeout: float = 30) -> str:
        """请求另一个 Agent 的回复（peer-to-peer RPC）"""
        req_id = f"peer_{uuid.uuid4().hex[:8]}"
        msg = Message(
            msg_type=MessageType.SYNC,
            sender=self.state.agent_id,
            receiver=target_id,
            content=prompt,
            task_id=task_id,
            metadata={"request_id": req_id, "expects_reply": True},
        )
        await self.bus.send(msg)

        # 等待回复
        deadline = time.time() + timeout
        while time.time() < deadline:
            reply = await self.bus.receive(self.state.agent_id, timeout=2)
            if reply and reply.metadata.get("request_id") == req_id:
                return reply.content
        return f"[TIMEOUT] {target_id} 未在 {timeout}s 内回复"

    async def listen_for_peers(self, handler: Callable = None,
                               timeout: float = 5) -> list:
        """监听来自其他 Agent 的消息，返回收到的消息列表"""
        received = []
        while True:
            msg = await self.bus.receive(self.state.agent_id, timeout=timeout)
            if msg is None:
                break
            received.append(msg)
            if handler:
                await handler(msg)
            elif msg.metadata.get("expects_reply"):
                # 自动回复：将消息转发给 LLM
                reply_content = await self.call_llm(msg.content)
                reply_msg = Message(
                    msg_type=MessageType.SYNC,
                    sender=self.state.agent_id,
                    receiver=msg.sender,
                    content=reply_content,
                    task_id=msg.task_id,
                    metadata={"request_id": msg.metadata.get("request_id")},
                )
                await self.bus.send(reply_msg)
        return received

    # ───────────────────── 知识检索（便捷方法） ─────────────────────

    async def search_knowledge(self, query: str, top_k: int = 3) -> str:
        """通过知识路由器检索知识"""
        if not self.knowledge_router:
            return ""
        try:
            results = await self.knowledge_router.search(query, top_k=top_k)
            if not results:
                return ""
            parts = []
            for r in results:
                parts.append(f"[{r.source}] {r.title}: {r.content[:300]}")
            return "\n".join(parts)
        except Exception as e:
            return f"[知识检索异常] {e}"

    # ───────────────────── 状态 ─────────────────────

    def get_status(self) -> dict:
        return {
            "id": self.state.agent_id,
            "name": self.state.name,
            "role": self.state.role,
            "status": self.state.status,
            "current_task": self.state.current_task,
            "tasks_completed": self.state.tasks_completed,
            "tasks_failed": self.state.tasks_failed,
            "capabilities": self.state.capabilities,
            "assist_roles": self.state.assist_roles,
            "uptime": round(time.time() - self.state.uptime_start, 0),
        }
