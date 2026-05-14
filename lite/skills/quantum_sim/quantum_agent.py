"""量子智能体 (Quantum Agent)

将量子计算概念映射到帝国架构的多智能体系统：
- 每个 Agent 可以处于"叠加态"——同时持有多个观点
- Agent 之间可以"纠缠"——一个的输出自动成为另一个的输入
- 测量操作让 Agent "坍缩"到一个确定的立场
- 时空复用让同一个 Agent 在不同时刻扮演不同角色

这不是真正的量子计算，而是用量子思维启发的 AI 协作模式。
"""
import math
import random
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from .qubit import QubitState, Qubit
from .gates import QuantumGate
from .entanglement import EntanglementChamber, EntangledPair
from .timeslice import TimeSpaceMultiplexer, TimeLine


@dataclass
class QuantumOpinion:
    """量子观点：Agent 对一个问题的多种可能立场"""
    question: str
    positions: list[str]           # 可能的立场
    amplitudes: list[complex]      # 每个立场的概率振幅
    is_collapsed: bool = False
    collapsed_position: str = ""

    def probabilities(self) -> list[float]:
        """计算每个立场的概率"""
        return [abs(a) ** 2 for a in self.amplitudes]

    def collapse(self) -> str:
        """测量坍缩：随机选择一个立场"""
        if self.is_collapsed:
            return self.collapsed_position

        probs = self.probabilities()
        total = sum(probs)
        probs = [p / total for p in probs]

        idx = random.choices(range(len(self.positions)), weights=probs, k=1)[0]
        self.is_collapsed = True
        self.collapsed_position = self.positions[idx]
        return self.collapsed_position

    def description(self) -> str:
        if self.is_collapsed:
            return f"📊 已确定立场: {self.collapsed_position}"

        lines = [f"🔮 叠加态观点: {self.question}"]
        probs = self.probabilities()
        for pos, prob in zip(self.positions, probs):
            bar = "█" * int(prob * 20)
            lines.append(f"  {bar} {prob:.1%} → {pos}")
        return "\n".join(lines)


class QuantumAgent:
    """量子智能体 — 帝国架构的量子增强版 Agent

    核心特性：
    1. 叠加思维：可以同时持有多个矛盾观点
    2. 纠缠协作：与其他 Agent 形成深度关联
    3. 测量坍缩：在需要时确定立场
    4. 量子行走：在决策空间中探索多条路径
    """

    def __init__(self, agent_id: str, name: str, specialties: list[str] = None):
        self.agent_id = agent_id
        self.name = name
        self.specialties = specialties or []
        self.opinions: dict[str, QuantumOpinion] = {}
        self.entangled_partners: list[str] = []
        self.timeline: Optional[TimeLine] = None
        self.qubit_state = Qubit.zero(f"{agent_id}_core")
        self.tasks_completed = 0

    def form_opinion(self, question: str, positions: list[str],
                     initial_bias: list[float] = None) -> QuantumOpinion:
        """形成量子观点 — 同时持有多个立场

        Args:
            question: 问题
            positions: 可能的立场列表
            initial_bias: 初始偏好（概率分布），None 则等权叠加
        """
        n = len(positions)
        if initial_bias is None:
            # 等权叠加
            amp = 1.0 / math.sqrt(n)
            amplitudes = [complex(amp, 0)] * n
        else:
            # 根据偏好设置振幅
            total = sum(initial_bias)
            amplitudes = [complex(math.sqrt(p / total), 0) for p in initial_bias]

        opinion = QuantumOpinion(
            question=question,
            positions=positions,
            amplitudes=amplitudes,
        )
        self.opinions[question] = opinion
        return opinion

    def entangle_with(self, other: 'QuantumAgent') -> EntangledPair:
        """与其他 Agent 建立纠缠

        纠缠后，两个 Agent 的观点会相互关联。
        当一个 Agent 确定立场时，另一个会自动调整。
        """
        pair = EntanglementChamber.create_bell_pair(
            label_a=f"{self.agent_id}_e",
            label_b=f"{other.agent_id}_e",
        )
        self.entangled_partners.append(other.agent_id)
        other.entangled_partners.append(self.agent_id)
        return pair

    def measure_opinion(self, question: str) -> str:
        """测量观点 — 坍缩到一个确定立场"""
        if question not in self.opinions:
            return f"未对此问题形成观点: {question}"
        return self.opinions[question].collapse()

    def quantum_debate(self, other: 'QuantumAgent', question: str,
                       rounds: int = 3) -> dict:
        """量子辩论 — 两个纠缠 Agent 就同一问题交换观点

        每一轮：
        1. 双方同时表达当前立场（叠加态）
        2. 通过纠缠交换信息
        3. 观点振幅更新
        """
        debate_log = []

        # 双方形成初始观点
        if question not in self.opinions:
            self.form_opinion(question, ["同意", "反对", "中立"])
        if question not in other.opinions:
            other.form_opinion(question, ["同意", "反对", "中立"])

        for round_i in range(rounds):
            # 测量双方立场
            pos_a = self.measure_opinion(question)
            pos_b = other.measure_opinion(question)

            debate_log.append({
                "round": round_i + 1,
                f"{self.name}": pos_a,
                f"{other.name}": pos_b,
                "alignment": pos_a == pos_b,
            })

            # 纠缠效应：如果立场一致，概率增强
            if pos_a == pos_b:
                self.form_opinion(question, [pos_a, "其他"],
                                  [0.8, 0.2])
                other.form_opinion(question, [pos_b, "其他"],
                                   [0.8, 0.2])
            else:
                # 立场不一致时，引入新的可能性
                all_positions = list(set(
                    self.opinions[question].positions +
                    other.opinions[question].positions
                ))
                self.form_opinion(question, all_positions)
                other.form_opinion(question, all_positions)

        return {
            "question": question,
            "debate_rounds": rounds,
            "log": debate_log,
            "final_a": self.opinions[question].description(),
            "final_b": other.opinions[question].description(),
        }

    def quantum_walk(self, steps: int = 5) -> list[str]:
        """量子行走 — 在决策空间中探索多条路径

        经典随机行走：每一步选择左或右
        量子行走：同时向左和右（叠加态），通过干涉产生概率分布
        """
        position = 0
        path = [position]

        for _ in range(steps):
            # Hadamard 创建叠加态
            q = Qubit.zero("walk")
            q = QuantumGate.hadamard(q)

            # 测量决定方向
            result = Qubit.measure(q)
            if result == 0:
                position -= 1  # 左
            else:
                position += 1  # 右
            path.append(position)

        return path

    def description(self) -> str:
        lines = [
            f"🤖 量子Agent: {self.name} [{self.agent_id}]",
            f"  专业: {', '.join(self.specialties) or '通用'}",
            f"  纠缠伙伴: {len(self.entangled_partners)}",
            f"  完成任务: {self.tasks_completed}",
        ]
        if self.opinions:
            lines.append("  观点:")
            for q, op in self.opinions.items():
                lines.append(f"    {op.description()}")
        return "\n".join(lines)


class QuantumSwarm:
    """量子群体 — 多个量子 Agent 的协作系统

    对应帝国架构的三公九卿制：
    - 丞相：总协调（量子仲裁者）
    - 参谋：多角度分析（叠加态观点）
    - 执行：任务执行（测量坍缩）
    """

    def __init__(self):
        self.agents: dict[str, QuantumAgent] = {}
        self.multiplexer = TimeSpaceMultiplexer()
        self.entanglement_pairs: list[EntangledPair] = []
        self.collaboration_log: list[dict] = []

    def add_agent(self, agent: QuantumAgent):
        """添加 Agent 到群体"""
        self.agents[agent.agent_id] = agent

    def create_parallel_agents(self, base_name: str, count: int,
                                specialties: list[str] = None) -> list[QuantumAgent]:
        """创建并行 Agent — 量子叠加版本

        不是创建多个 Agent，而是创建一个 Agent 的多个"叠加态分身"
        """
        agents = []
        for i in range(count):
            agent = QuantumAgent(
                agent_id=f"{base_name}_q{i}",
                name=f"{base_name}⊗{i}",
                specialties=specialties or [],
            )
            self.agents[agent.agent_id] = agent
            agents.append(agent)
        return agents

    def entangle_agents(self, agent_a_id: str, agent_b_id: str):
        """在两个 Agent 之间建立纠缠"""
        if agent_a_id in self.agents and agent_b_id in self.agents:
            pair = self.agents[agent_a_id].entangle_with(self.agents[agent_b_id])
            self.entanglement_pairs.append(pair)

    def quantum_collaboration(self, task: str, agent_ids: list[str] = None) -> dict:
        """量子协作 — 多个 Agent 通过叠加态和纠缠共同完成任务

        流程：
        1. 每个 Agent 形成对任务的叠加态观点
        2. 通过纠缠交换信息
        3. 测量坍缩得到最终结果
        """
        if agent_ids is None:
            agent_ids = list(self.agents.keys())

        agents = [self.agents[aid] for aid in agent_ids if aid in self.agents]

        # 每个 Agent 形成叠加态观点
        opinions = {}
        for agent in agents:
            op = agent.form_opinion(
                task,
                ["方案A", "方案B", "方案C", "方案D"],
            )
            opinions[agent.name] = op

        # 测量坍缩
        results = {}
        for agent in agents:
            result = agent.measure_opinion(task)
            results[agent.name] = result

        # 统计
        alignment = len(set(results.values())) == 1

        collab = {
            "task": task,
            "agents": list(results.keys()),
            "results": results,
            "full_alignment": alignment,
            "opinions": {k: v.description() for k, v in opinions.items()},
        }

        self.collaboration_log.append(collab)
        return collab

    def visualize_network(self) -> str:
        """可视化 Agent 纠缠网络"""
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║              量子纠缠网络 (Entanglement Network)          ║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
        ]

        for aid, agent in self.agents.items():
            icon = "🔮" if agent.opinions else "🤖"
            lines.append(f"  {icon} {agent.name} [{aid}]")
            if agent.entangled_partners:
                for pid in agent.entangled_partners:
                    if pid in self.agents:
                        lines.append(f"    🔗 ←→ {self.agents[pid].name}")

        if self.entanglement_pairs:
            lines.append("")
            lines.append("  纠缠对:")
            for pair in self.entanglement_pairs:
                lines.append(f"    {pair.description()}")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """获取群体统计"""
        return {
            "total_agents": len(self.agents),
            "entangled_pairs": len(self.entanglement_pairs),
            "collaborations": len(self.collaboration_log),
            "total_opinions": sum(
                len(a.opinions) for a in self.agents.values()
            ),
        }
