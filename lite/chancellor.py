"""帝国架构 - 丞相协调器 (v1.6)

v1.6 新增：
- 丞相并行分发 + 超时保护
- 查曹自动触发知识路由
- Peer-to-peer 去中心化协作
- 节点超时 + 失败重试
- 柔性角色调度
"""
import asyncio
import json
import re
import uuid
import time
from core.bus import MessageBus, Message, MessageType
from core.tokens import TokenTracker
from core.security import SecuritySystem, ViolationLevel
from agents.base import Agent, DEFAULT_TASK_TIMEOUT
from core.config import load_empire_config
from core.keju import ImperialExamination, ExaminationType, Rank


# v1.6: 丞相指令分析超时
PLAN_TIMEOUT = 45
# v1.6: 单节点执行超时
NODE_TIMEOUT = 60
# v1.6: 汇总超时
SUMMARY_TIMEOUT = 45


class Chancellor:
    """丞相 - 总协调器 (v1.6)"""

    def __init__(self):
        self.config = load_empire_config()
        self.bus = MessageBus()
        self.tracker = TokenTracker()
        self.security = SecuritySystem()
        self.agents: dict[str, Agent] = {}
        # v1.6: 知识层（由 mount_knowledge 注入）
        self.knowledge_router = None
        self.hanlin_director = None
        self.knowledge_audit = None
        # v1.6: 科举制度
        self.keju = ImperialExamination()
        self._init_agents()

    def _init_agents(self):
        """初始化所有节点 — 支持 v1.6 柔性角色"""
        cfg = self.config["agents"]

        # 丞相
        c = cfg["chancellor"]
        self.agents["chancellor"] = Agent(
            "chancellor", c["name"], c["role"], c["system_prompt"],
            self.bus, self.tracker,
            capabilities=c.get("capabilities", []),
            assist_roles=c.get("assist_roles", []),
        )

        # 参谋
        for a in cfg["advisors"]:
            self.agents[a["id"]] = Agent(
                a["id"], a["name"], a["role"], a["system_prompt"],
                self.bus, self.tracker,
                capabilities=a.get("capabilities", []),
                assist_roles=a.get("assist_roles", []),
            )

        # 执行层
        for a in cfg["executors"]:
            self.agents[a["id"]] = Agent(
                a["id"], a["name"], a["role"], a["system_prompt"],
                self.bus, self.tracker,
                capabilities=a.get("capabilities", []),
                assist_roles=a.get("assist_roles", []),
            )

        # 锦衣卫
        s = cfg["security"]
        self.agents[s["id"]] = Agent(
            s["id"], s["name"], s["role"], s["system_prompt"],
            self.bus, self.tracker,
            capabilities=s.get("capabilities", []),
            assist_roles=s.get("assist_roles", []),
        )

    def _inject_knowledge(self):
        """将知识路由器注入到所有 Agent"""
        if self.knowledge_router:
            for agent in self.agents.values():
                agent.knowledge_router = self.knowledge_router

    async def receive_command(self, command: str) -> dict:
        """接收皇帝指令并编排执行 (v1.6 并行版)"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        start = time.time()

        # 确保知识层已注入
        self._inject_knowledge()

        # Step 1: 丞相分析指令，决定需要哪些节点
        plan = await self._plan(task_id, command)

        # Step 2: 并行执行（v1.6: 带超时保护）
        results = await self._execute_plan(task_id, command, plan)

        # Step 3: v1.6: 节点间 peer-to-peer 补充（可选）
        p2p_results = await self._p2p_phase(task_id, command, results)
        if p2p_results:
            results["p2p_supplement"] = p2p_results

        # Step 4: 锦衣卫审计
        audit = await self._audit(task_id, command, results)

        elapsed = round(time.time() - start, 1)

        return {
            "task_id": task_id,
            "command": command,
            "plan": plan,
            "results": results,
            "audit": audit,
            "elapsed_seconds": elapsed,
            "tokens_used": self.tracker.get_total_today(),
            "nodes_status": {
                aid: a.get_status() for aid, a in self.agents.items()
            },
        }

    async def _plan(self, task_id: str, command: str) -> dict:
        """丞相规划任务 (v1.6: 柔性调度 + 知识路由提示)"""

        # 构建节点能力描述
        node_descs = []
        for aid, agent in self.agents.items():
            if aid == "chancellor":
                continue
            caps = ", ".join(agent.state.capabilities) if agent.state.capabilities else agent.state.role
            assists = ", ".join(agent.state.assist_roles[:3]) if agent.state.assist_roles else ""
            desc = f"- {agent.state.name} ({aid}): 擅长[{caps}]"
            if assists:
                desc += f" 可协助[{assists}]"
            node_descs.append(desc)

        chancellor = self.agents["chancellor"]
        plan_prompt = f"""皇帝下达指令：{command}

可用节点及能力：
{chr(10).join(node_descs)}

调度原则：
1. 优先按角色匹配，但允许跨角色协助
2. 涉及信息/知识的任务必须包含查曹
3. 鼓励并行执行
4. 不要让节点闲置——即使任务不完全对口，也分配辅助工作

请返回 JSON 格式：
{{
  "tasks": [
    {{"agent_id": "节点id", "prompt": "具体任务描述", "priority": 1-10}}
  ],
  "parallel": true,
  "p2p_enabled": false
}}

只返回 JSON，不要其他内容。"""

        try:
            result = await asyncio.wait_for(
                chancellor.call_llm(plan_prompt),
                timeout=PLAN_TIMEOUT,
            )
        except asyncio.TimeoutError:
            result = ""

        # 解析 JSON
        plan = None
        if result:
            try:
                raw = result
                if "```" in raw:
                    parts = raw.split("```")
                    for p in parts:
                        p = p.strip()
                        if p.startswith("json"):
                            p = p[4:].strip()
                        if p.startswith("{"):
                            plan = json.loads(p)
                            break
                else:
                    # 找到第一个 { 到最后一个 }
                    start_idx = raw.find("{")
                    end_idx = raw.rfind("}")
                    if start_idx >= 0 and end_idx > start_idx:
                        plan = json.loads(raw[start_idx:end_idx + 1])
            except Exception:
                plan = None

        if not plan:
            # v1.6 默认方案：全员参与 + 并行 + 查曹自动知识检索
            plan = {
                "tasks": [
                    {"agent_id": "advisor_strategy",
                     "prompt": f"分析这个指令的战略意图、风险和多角度方案：{command}", "priority": 3},
                    {"agent_id": "advisor_tech",
                     "prompt": f"评估技术可行性和推荐方案：{command}", "priority": 3},
                    {"agent_id": "advisor_intel",
                     "prompt": f"收集相关信息和数据支持：{command}", "priority": 3},
                    {"agent_id": "executor_researcher",
                     "prompt": f"检索相关知识并整理调研结果：{command}", "priority": 2},
                    {"agent_id": "executor_writer",
                     "prompt": f"基于以上分析，准备一份结构化的内容框架：{command}", "priority": 5},
                    {"agent_id": "executor_coder",
                     "prompt": f"如果需要代码或工具支持，准备相关方案：{command}", "priority": 6},
                ],
                "parallel": True,
                "p2p_enabled": True,
            }

        return plan

    async def _execute_plan(self, task_id: str, command: str,
                            plan: dict) -> dict:
        """执行计划 (v1.6: 并行分发 + 超时 + 重试)"""
        results = {}
        tasks = plan.get("tasks", [])
        p2p_enabled = plan.get("p2p_enabled", False)
        v16_cfg = self.config.get("v16_features", {})
        node_timeout = v16_cfg.get("node_timeout_seconds", NODE_TIMEOUT)

        if plan.get("parallel", True):
            # ─────── 并行执行（v1.6: asyncio.gather + 超时）───────
            async def run_task(t):
                agent_id = t.get("agent_id", "")
                if agent_id not in self.agents:
                    return agent_id, {"error": f"未知节点: {agent_id}"}

                prompt = t.get("prompt", command)
                priority = t.get("priority", 5)

                # v1.6: 查曹自动触发知识路由
                context = ""
                if agent_id == "executor_researcher" and self.knowledge_router:
                    knowledge_context = await self._auto_knowledge_search(command, prompt)
                    if knowledge_context:
                        context = f"知识检索结果（自动获取）：\n{knowledge_context}\n\n请基于以上知识完成你的任务。"

                r = await self.agents[agent_id].process_task(
                    task_id, prompt, context=context, timeout=node_timeout,
                )
                return agent_id, {
                    "result": r,
                    "priority": priority,
                    "knowledge_used": bool(context),
                }

            coros = [run_task(t) for t in tasks]
            done = await asyncio.gather(*coros, return_exceptions=True)
            for item in done:
                if isinstance(item, Exception):
                    results["gather_error"] = {"error": str(item)}
                else:
                    results[item[0]] = item[1]
        else:
            # ─────── 串行执行 ───────
            for t in tasks:
                agent_id = t.get("agent_id", "")
                if agent_id not in self.agents:
                    continue
                prompt = t.get("prompt", command)
                context = ""
                if agent_id == "executor_researcher" and self.knowledge_router:
                    context = await self._auto_knowledge_search(command, prompt)
                r = await self.agents[agent_id].process_task(
                    task_id, prompt, context=context, timeout=node_timeout,
                )
                results[agent_id] = {"result": r, "knowledge_used": bool(context)}

        # ─────── 科举考核：记录每个节点的表现 ───────
        self._evaluate_nodes(task_id, results)

        # ─────── 丞相汇总 ───────
        summary = await self._summarize(task_id, command, results)
        results["chancellor_summary"] = summary

        return results

    async def _auto_knowledge_search(self, command: str,
                                     task_prompt: str) -> str:
        """v1.6: 查曹自动知识检索"""
        if not self.knowledge_router:
            return ""

        # 从指令和任务 prompt 中提取关键词
        search_queries = [command]
        # 简单关键词提取：取 prompt 中的中文词组和英文单词
        # 提取 2-8 字中文词组
        cn_words = re.findall(r'[\u4e00-\u9fff]{2,8}', task_prompt)
        for w in cn_words[:3]:
            if w not in search_queries[0]:
                search_queries.append(w)

        all_results = []
        for query in search_queries[:2]:  # 最多搜索 2 次
            try:
                results = await self.knowledge_router.search(query, top_k=2)
                all_results.extend(results)
            except Exception:
                pass

        if not all_results:
            return ""

        parts = []
        for r in all_results[:4]:
            parts.append(f"[{r.source}] {r.title}: {r.content[:200]}")
        return "\n".join(parts)

    async def _p2p_phase(self, task_id: str, command: str,
                         results: dict) -> dict:
        """v1.6: Peer-to-peer 补充阶段

        让关键节点之间直接通信，补充丞相调度可能遗漏的协作。
        例如：技术参谋可以请求查曹补充技术文档检索。
        """
        v16_cfg = self.config.get("v16_features", {})
        if not v16_cfg.get("p2p_collaboration", False):
            return {}

        p2p_results = {}

        # 定义有意义的 peer 协作对
        peer_pairs = [
            ("advisor_tech", "executor_researcher",
             "请帮我检索与当前技术方案相关的最新资料或文档"),
            ("advisor_strategy", "advisor_intel",
             "请补充与战略分析相关的市场数据或竞品信息"),
            ("executor_writer", "advisor_strategy",
             "请帮我确认写作框架的逻辑结构是否合理"),
        ]

        for requester_id, provider_id, default_prompt in peer_pairs:
            if requester_id not in results or provider_id not in results:
                continue
            # 只有当两个节点都成功执行时才触发 P2P
            req_result = results.get(requester_id, {})
            if isinstance(req_result, dict) and "error" not in req_result:
                try:
                    requester = self.agents[requester_id]
                    reply = await asyncio.wait_for(
                        requester.request_from_peer(
                            provider_id, default_prompt,
                            task_id=task_id, timeout=20,
                        ),
                        timeout=25,
                    )
                    if reply and not reply.startswith("[TIMEOUT"):
                        p2p_results[f"{requester_id}→{provider_id}"] = reply
                except (asyncio.TimeoutError, Exception):
                    pass

        return p2p_results

    async def _summarize(self, task_id: str, command: str,
                         results: dict) -> str:
        """丞相汇总结果"""
        chancellor = self.agents["chancellor"]

        summary_prompt = f"皇帝指令：{command}\n\n各节点执行结果：\n"
        for aid, r in results.items():
            if aid == "chancellor_summary":
                continue
            agent = self.agents.get(aid)
            name = agent.state.name if agent else aid
            if isinstance(r, dict):
                content = r.get("result", str(r))
                knowledge_tag = " 📚" if r.get("knowledge_used") else ""
            else:
                content = str(r)
                knowledge_tag = ""
            summary_prompt += f"\n【{name}{knowledge_tag}】\n{content[:800]}\n"

        summary_prompt += """
请汇总以上结果，给皇帝一份结构化汇报，包含：
1. 核心结论（3-5 句话）
2. 各节点关键贡献
3. 下一步建议
"""

        try:
            summary = await asyncio.wait_for(
                chancellor.call_llm(summary_prompt),
                timeout=SUMMARY_TIMEOUT,
            )
        except asyncio.TimeoutError:
            summary = "[丞相汇总超时] 请查看各节点原始输出。"
        return summary

    async def _audit(self, task_id: str, command: str,
                     results: dict) -> dict:
        """锦衣卫审计"""
        jw = self.agents["jinyiwei"]

        # 截取结果摘要
        results_summary = ""
        for aid, r in results.items():
            if aid == "chancellor_summary":
                continue
            if isinstance(r, dict):
                content = r.get("result", "")
            else:
                content = str(r)
            results_summary += f"{aid}: {content[:300]}\n"

        audit_prompt = f"""安全审计：
皇帝指令：{command}
执行结果摘要：
{results_summary[:2000]}

请检查：
1. 是否有数据外泄风险
2. 输出是否包含敏感信息（API key、密码等）
3. 是否有越权操作

返回 JSON：{{"safe": true/false, "issues": [], "level": 0}}"""

        try:
            audit_result = await asyncio.wait_for(
                jw.call_llm(audit_prompt),
                timeout=30,
            )
        except asyncio.TimeoutError:
            return {"safe": True, "issues": ["审计超时，默认通过"], "level": 0}

        try:
            raw = audit_result
            if "```" in raw:
                parts = raw.split("```")
                for p in parts:
                    p = p.strip()
                    if p.startswith("json"):
                        p = p[4:].strip()
                    if p.startswith("{"):
                        return json.loads(p)
            else:
                start_idx = raw.find("{")
                end_idx = raw.rfind("}")
                if start_idx >= 0 and end_idx > start_idx:
                    return json.loads(raw[start_idx:end_idx + 1])
        except Exception:
            pass

        return {"safe": True, "issues": ["审计解析失败，默认通过"], "level": 0}

    def _evaluate_nodes(self, task_id: str, results: dict):
        """科举考核：每次任务后评估节点表现"""
        if not self.keju:
            return
        for aid, r in results.items():
            if aid in ("chancellor_summary", "p2p_supplement", "gather_error"):
                continue
            if isinstance(r, dict) and "error" not in r:
                content = r.get("result", "")
                success = not content.startswith("[ERROR]") and not content.startswith("[TIMEOUT]")
                # 默认 10s 作为基准（实际应从 agent 追踪）
                node_elapsed = 10.0
                knowledge_bonus = 1.0 if r.get("knowledge_used") else 0.0
                self.keju.evaluate_task(
                    candidate_id=aid,
                    task_result=content,
                    task_elapsed=node_elapsed,
                    success=success,
                    collaboration_bonus=knowledge_bonus,
                )

    async def run_examination_cycle(self) -> list:
        """丞相主持科举周期 — 自动考核候补和官员"""
        results = []
        # 翰林院进修
        await self.keju.run_training_cycle(self.agents.get("chancellor"))
        # 晋升考试
        await self.keju.run_promotion_cycle(self.agents.get("chancellor"))
        return results

    def get_status(self) -> dict:
        """获取帝国状态"""
        return {
            "version": self.config.get("empire", {}).get("version", "unknown"),
            "agents": {aid: a.get_status() for aid, a in self.agents.items()},
            "tokens": self.tracker.get_usage(),
            "security": self.security.get_status(),
            "message_history": len(self.bus.history),
            "knowledge_layer": {
                "router_loaded": self.knowledge_router is not None,
                "sources": self.knowledge_router.list_sources() if self.knowledge_router else [],
            },
            "keju": self.keju.get_full_status() if self.keju else None,
        }
