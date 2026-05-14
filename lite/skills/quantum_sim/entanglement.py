"""量子纠缠 (Quantum Entanglement)

纠缠是量子力学最奇特的现象：两个粒子形成关联，无论相距多远，
测量其中一个会瞬间确定另一个的状态。

爱因斯坦称之为 "鬼魅般的超距作用" (spooky action at a distance)。

在帝国架构中，纠缠对应两个 Agent 之间的深度协作——
一个 Agent 的决策会立即影响另一个 Agent 的行为模式。
"""
import math
import random
from dataclasses import dataclass, field
from .qubit import QubitState, Qubit
from .gates import QuantumGate


@dataclass
class EntangledPair:
    """纠缠粒子对"""
    qubit_a: QubitState
    qubit_b: QubitState
    bell_state: str  # Bell 态名称
    entangled_at: float = 0.0
    measured: bool = False
    measurement_a: int = -1
    measurement_b: int = -1

    def description(self) -> str:
        """人类可读的纠缠态描述"""
        if self.measured:
            return (f"📎 已测量 Bell 态 {self.bell_state}\n"
                    f"  粒子A: |{self.measurement_a}⟩  粒子B: |{self.measurement_b}⟩")

        # Bell 态数学描述
        bell_desc = {
            "Φ+": "(|00⟩ + |11⟩) / √2",
            "Φ-": "(|00⟩ - |11⟩) / √2",
            "Ψ+": "(|01⟩ + |10⟩) / √2",
            "Ψ-": "(|01⟩ - |10⟩) / √2",
        }
        desc = bell_desc.get(self.bell_state, "未知态")
        return f"🔗 纠缠态 {self.bell_state}: {desc}"


class EntanglementChamber:
    """纠缠室 — 创建和管理量子纠缠对"""

    # Bell 态类型
    BELL_STATES = ["Φ+", "Φ-", "Ψ+", "Ψ-"]

    @staticmethod
    def create_bell_pair(bell_state: str = "Φ+",
                         label_a: str = "eA", label_b: str = "eB") -> EntangledPair:
        """创建 Bell 纠缠对

        Φ+ = (|00⟩ + |11⟩) / √2  →  H + CNOT
        Φ- = (|00⟩ - |11⟩) / √2  →  H + CNOT + Z
        Ψ+ = (|01⟩ + |10⟩) / √2  →  H + CNOT + X
        Ψ- = (|01⟩ - |10⟩) / √2  →  H + CNOT + Z + X
        """
        # 从 |00⟩ 开始
        qa = Qubit.zero(label_a)
        qb = Qubit.zero(label_b)

        # Hadamard on control
        qa = QuantumGate.hadamard(qa)

        # CNOT
        qa, qb = QuantumGate.cnot(qa, qb)

        # 根据 Bell 态类型添加额外门
        if bell_state == "Φ-":
            qa = QuantumGate.pauli_z(qa)
        elif bell_state == "Ψ+":
            qa = QuantumGate.pauli_x(qa)
        elif bell_state == "Ψ-":
            qa = QuantumGate.pauli_z(qa)
            qa = QuantumGate.pauli_x(qa)

        import time
        return EntangledPair(
            qubit_a=qa, qubit_b=qb,
            bell_state=bell_state,
            entangled_at=time.time(),
        )

    @staticmethod
    def measure_pair(pair: EntangledPair) -> tuple[int, int]:
        """测量纠缠对 — 关键特性：测量结果完全关联

        对于 Φ+ 态：
        - 测量 A 得到 0 → B 必定是 0
        - 测量 A 得到 1 → B 必定是 1

        对于 Ψ+ 态：
        - 测量 A 得到 0 → B 必定是 1
        - 测量 A 得到 1 → B 必定是 0
        """
        if pair.measured:
            return pair.measurement_a, pair.measurement_b

        # 测量粒子 A
        result_a = Qubit.measure(pair.qubit_a)

        # 根据 Bell 态确定 B 的结果（纠缠关联）
        if pair.bell_state in ("Φ+", "Φ-"):
            result_b = result_a  # 同向关联
        else:
            result_b = 1 - result_a  # 反向关联

        pair.measured = True
        pair.measurement_a = result_a
        pair.measurement_b = result_b

        # 坍缩状态
        pair.qubit_a, _ = Qubit.measure_with_collapse(pair.qubit_a)
        pair.qubit_b, _ = Qubit.measure_with_collapse(pair.qubit_b)

        return result_a, result_b

    @staticmethod
    def classical_correlation_test(n_pairs: int = 1000,
                                   bell_state: str = "Φ+") -> dict:
        """经典关联性测试 — 验证纠缠的统计特性

        对大量纠缠对进行测量，统计关联度。
        对于真正的纠缠态，关联度应为 100%。
        """
        correlations = 0
        results_a = []
        results_b = []

        for _ in range(n_pairs):
            pair = EntanglementChamber.create_bell_pair(bell_state)
            ra, rb = EntanglementChamber.measure_pair(pair)
            results_a.append(ra)
            results_b.append(rb)
            if ra == rb:
                correlations += 1

        correlation_rate = correlations / n_pairs

        return {
            "bell_state": bell_state,
            "total_pairs": n_pairs,
            "correlations": correlations,
            "correlation_rate": f"{correlation_rate:.1%}",
            "is_entangled": correlation_rate > 0.95,
            "avg_a": sum(results_a) / len(results_a),
            "avg_b": sum(results_b) / len(results_b),
        }

    @staticmethod
    def bell_inequality_test(n_samples: int = 1000) -> dict:
        """Bell 不等式违反测试

        经典局域隐变量理论预测：S ≤ 2
        量子力学预测：S = 2√2 ≈ 2.83

        这是验证量子力学非局域性的核心实验。
        """
        S_values = []

        for _ in range(10):  # 多次测量取平均
            # 模拟 CHSH 不等式
            # 使用随机角度进行测量
            alice_angle = random.uniform(0, math.pi)
            bob_angle = random.uniform(0, math.pi)

            # 量子关联
            E = -math.cos(alice_angle - bob_angle)
            S_values.append(abs(2 * E))

        S_avg = sum(S_values) / len(S_values)

        return {
            "S_value": round(S_avg, 4),
            "classical_limit": 2.0,
            "quantum_limit": round(2 * math.sqrt(2), 4),
            "violates_inequality": S_avg > 2.0,
            "interpretation": (
                "违反 Bell 不等式！量子非局域性得到验证。"
                if S_avg > 2.0
                else "未违反（可能需要更多样本）"
            ),
        }
