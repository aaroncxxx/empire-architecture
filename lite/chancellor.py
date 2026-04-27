"""帝国架构 - 丞相协调器 v2.0"""
import asyncio
import json
import re
import uuid
import time
from core.bus import MessageBus, Message, MessageType
from core.tokens import TokenTracker
from core.security import SecuritySystem, ViolationLevel
from agents.base import Agent
from core.config import load_empire_config


def _extract_json(text: str) -> dict | None:
    """从 LLM 输出中稳健提取 JSON"""
    # 1. 尝试直接解析
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 提取 ```json ... ``` 代码块
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. 提取第一个 { ... } 块（贪婪匹配最外层）
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
    return None


class Chancellor:
    """丞相 - 总协调器"""

    def __init__(self):
        self.config = load_empire_config()
        self.bus = MessageBus()
        self.tracker = TokenTracker()
        self.security = SecuritySystem()
        self.agents: dict[str, Agent] = {}
        self.knowledge_router = None
        self.hanlin_director = None
        self.knowledge_audit = None
        self._init_agents()
        self._init_knowledge()

    def _init_agents(self):
        """初始化所有节点"""
        cfg = self.config["agents"]

        def _add(key, items=None):
            if items is None:
                items = [cfg[key]]
            else:
                items = cfg.get(key, [])
            for a in items if isinstance(items, list) else [items]:
                aid = a.get("id", key)
                self.agents[aid] = Agent(
                    aid, a["name"], a["role"], a["system_prompt"],
                    self.bus, self.tracker,
                )

        _add("chancellor")
        for section in ["advisors", "executors", "ministries", "scholars",
                         "special", "overseers", "extra"]:
            for a in cfg.get(section, []):
                self.agents[a["id"]] = Agent(
                    a["id"], a["name"], a["role"], a["system_prompt"],
                    self.bus, self.tracker,
                )
        s = cfg["security"]
        self.agents[s["id"]] = Agent(
            s["id"], s["name"], s["role"], s["system_prompt"],
            self.bus, self.tracker,
        )

    def _init_knowledge(self):
        """挂载知识层（静默，失败不阻塞主流程）"""
        try:
            from knowledge.mount import mount_knowledge
            kb = mount_knowledge(self)
            self.knowledge_router = kb["router"]
            self.hanlin_director = kb["director"]
            self.knowledge_audit = kb["audit"]
        except Exception:
            pass

    async def _query_knowledge(self, query: str, top_k: int = 3) -> str:
        """检索知识库，返回拼接上下文"""
        if not self.knowledge_router:
            return ""
        try:
            results = await self.knowledge_router.search(query, top_k)
            if not results:
                return ""
            parts = []
            for r in results:
                if r.title == "ERROR" or r.title == "⏳ 待皇帝批准":
                    continue
                parts.append(f"[{r.source}] {r.title}: {r.content[:300]}")
            return "\n".join(parts) if parts else ""
        except Exception:
            return ""

    async def receive_command(self, command: str) -> dict:
        """接收皇帝指令并编排执行"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        start = time.time()

        # Step 0: 知识预检索
        knowledge_context = await self._query_knowledge(command)

        # Step 1: 丞相规划
        plan = await self._plan(task_id, command, knowledge_context)

        # Step 2: 并行执行（注入知识上下文）
        results = await self._execute_plan(task_id, command, plan, knowledge_context)

        # Step 3: 锦衣卫审计
        audit = await self._audit(task_id, command, results)

        elapsed = round(time.time() - start, 1)

        # Step 4: 知识审计记录
        if self.knowledge_audit and knowledge_context:
            self.knowledge_audit.log_search(
                "chancellor", "丞相", command, "multi",
                len(results), 0.0, elapsed_ms=int(elapsed * 1000),
            )

        return {
            "task_id": task_id,
            "command": command,
            "plan": plan,
            "results": results,
            "audit": audit,
            "elapsed_seconds": elapsed,
            "tokens_used": self.tracker.get_total_today(),
            "knowledge_used": bool(knowledge_context),
        }

    async def _plan(self, task_id: str, command: str,
                    knowledge_context: str = "") -> dict:
        """丞相规划任务"""
        chancellor = self.agents["chancellor"]

        agent_list = []
        for aid, agent in self.agents.items():
            if aid == "chancellor":
                continue
            agent_list.append(f"- {agent.state.name} ({aid})：{agent.state.role}")

        agents_text = "\n".join(agent_list)

        plan_prompt = f"""皇帝下达指令：{command}

可用节点（共{len(self.agents)}个）：
{agents_text}"""

        if knowledge_context:
            plan_prompt += f"\n\n已检索到的相关知识：\n{knowledge_context}"

        plan_prompt += """

请根据任务需求，选择最合适的节点组合。返回 JSON 格式：
1. tasks: 列表，每个任务包含 agent_id, prompt, priority
2. parallel: 是否并行执行

只返回 JSON，不要其他内容。"""

        result = await chancellor.call_llm(plan_prompt)
        plan = _extract_json(result)

        if not plan or "tasks" not in plan:
            # 智能 fallback：根据任务关键词选择节点
            plan = self._smart_fallback(command)

        return plan

    def _smart_fallback(self, command: str) -> dict:
        """根据任务关键词智能选择节点组合"""
        cmd = command.lower()
        tasks = []

        # 默认参谋团
        tasks.append({"agent_id": "advisor_strategy", "prompt": f"战略分析：{command}", "priority": 3})
        tasks.append({"agent_id": "advisor_tech", "prompt": f"技术评估：{command}", "priority": 3})
        tasks.append({"agent_id": "advisor_intel", "prompt": f"情报收集：{command}", "priority": 3})

        # 关键词匹配
        if any(k in cmd for k in ["写", "文", "报告", "总结", "文章", "作文"]):
            tasks.append({"agent_id": "executor_writer", "prompt": f"撰写：{command}", "priority": 2})
        if any(k in cmd for k in ["代码", "程序", "脚本", "开发", "python", "api"]):
            tasks.append({"agent_id": "executor_coder", "prompt": f"编码：{command}", "priority": 2})
        if any(k in cmd for k in ["查", "搜索", "调研", "资料", "知识"]):
            tasks.append({"agent_id": "executor_researcher", "prompt": f"检索：{command}", "priority": 2})
        if any(k in cmd for k in ["安全", "审计", "风险", "检查"]):
            tasks.append({"agent_id": "jinyiwei", "prompt": f"安全审查：{command}", "priority": 1})
        if any(k in cmd for k in ["翻译", "英文", "日文", "多语言"]):
            tasks.append({"agent_id": "extra_ambassador", "prompt": f"翻译：{command}", "priority": 2})
        if any(k in cmd for k in ["创意", "设计", "美化", "润色"]):
            tasks.append({"agent_id": "extra_treasury", "prompt": f"创意美化：{command}", "priority": 2})
        if any(k in cmd for k in ["趋势", "预测", "未来", "预警"]):
            tasks.append({"agent_id": "special_astrologer", "prompt": f"趋势预测：{command}", "priority": 2})

        return {"tasks": tasks, "parallel": True}

    async def _execute_plan(self, task_id: str, command: str, plan: dict,
                            knowledge_context: str = "") -> dict:
        """执行计划"""
        results = {}
        tasks = plan.get("tasks", [])

        async def run_task(t):
            agent_id = t.get("agent_id", "")
            if agent_id in self.agents:
                prompt = t.get("prompt", command)
                # 注入知识上下文
                ctx = knowledge_context if knowledge_context else ""
                r = await self.agents[agent_id].process_task(task_id, prompt, ctx)
                return agent_id, r
            return agent_id, f"[ERROR] 未知节点: {agent_id}"

        if plan.get("parallel", True):
            coros = [run_task(t) for t in tasks]
            done = await asyncio.gather(*coros, return_exceptions=True)
            for item in done:
                if isinstance(item, Exception):
                    results["error"] = str(item)
                else:
                    results[item[0]] = item[1]
        else:
            for t in tasks:
                agent_id, r = await run_task(t)
                results[agent_id] = r

        # 丞相汇总
        summary_prompt = f"皇帝指令：{command}\n\n各节点执行结果：\n"
        for aid, r in results.items():
            name = self.agents[aid].state.name if aid in self.agents else aid
            summary_prompt += f"\n【{name}】\n{r}\n"
        summary_prompt += "\n请汇总以上结果，给皇帝一份简洁的汇报。"

        summary = await self.agents["chancellor"].call_llm(summary_prompt)
        results["chancellor_summary"] = summary

        return results

    async def _audit(self, task_id: str, command: str, results: dict) -> dict:
        """锦衣卫审计"""
        jw = self.agents["jinyiwei"]
        audit_prompt = f"""安全审计：
皇帝指令：{command}
执行结果摘要：{str(results)[:2000]}

请检查：
1. 是否有数据外泄风险
2. 输出是否包含敏感信息
3. 是否有越权操作

返回 JSON：{{"safe": true/false, "issues": [], "level": 0}}"""

        audit_result = await jw.call_llm(audit_prompt)
        audit = _extract_json(audit_result)

        if not audit or "safe" not in audit:
            audit = {"safe": True, "issues": ["审计解析失败，默认通过"], "level": 0}

        return audit

    def get_status(self) -> dict:
        """获取帝国状态"""
        status = {
            "agents": {aid: a.get_status() for aid, a in self.agents.items()},
            "tokens": self.tracker.get_usage(),
            "security": self.security.get_status(),
            "message_history": len(self.bus.history),
        }
        if self.knowledge_router:
            status["knowledge_sources"] = self.knowledge_router.list_sources()
        if self.hanlin_director:
            status["hanlin"] = self.hanlin_director.get_status()
        return status
