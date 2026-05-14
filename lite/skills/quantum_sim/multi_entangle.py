"""多比特纠缠态 (Multi-Qubit Entanglement)

经典纠缠态：
- Bell 态: 2 qubits, 4 种 (Φ±, Ψ±)
- GHZ 态: n qubits, (|00...0⟩ + |11...1⟩) / √2
- W 态:   n qubits, (|100⟩ + |010⟩ + |001⟩) / √3

GHZ 态的意义：
- 最大纠缠态，所有 qubit 测量结果完全关联
- 量子密钥分发的基础
- 测试量子力学非局域性的核心资源
"""
import math
import time
from dataclasses import dataclass, field
from .qubit import QubitState, Qubit, QuantumRegister
from .gates import QuantumGate, CircuitVisualizer
from .entanglement import EntanglementChamber


class GHZState:
    """GHZ 态 (Greenberger-Horne-Zeilinger)

    |GHZ_n⟩ = (|00...0⟩ + |11...1⟩) / √2

    关键特性：测量结果只有全0或全1，概率各50%
    """

    @staticmethod
    def create_3qubit() -> dict:
        """制备 3-qubit GHZ 态（返回完整状态向量）"""
        n = 3
        dim = 2 ** n
        # 状态向量：只有 |000⟩ 和 |111⟩ 有振幅
        state = [complex(0)] * dim
        v = 1 / math.sqrt(2)
        state[0b000] = complex(v, 0)  # |000⟩
        state[0b111] = complex(v, 0)  # |111⟩
        return {
            "n_qubits": n,
            "state_vector": state,
            "basis_labels": [f"|{i:0{n}b}⟩" for i in range(dim)],
        }

    @staticmethod
    def create_nqubit(n: int) -> dict:
        """制备 n-qubit GHZ 态"""
        if n < 2:
            raise ValueError("GHZ 态至少需要 2 个 qubit")
        dim = 2 ** n
        state = [complex(0)] * dim
        v = 1 / math.sqrt(2)
        state[0] = complex(v, 0)        # |00...0⟩
        state[dim - 1] = complex(v, 0)  # |11...1⟩
        return {
            "n_qubits": n,
            "state_vector": state,
            "basis_labels": [f"|{i:0{n}b}⟩" for i in range(dim)],
        }

    @staticmethod
    def measure(ghz: dict, shots: int = 1000) -> dict:
        """测量 GHZ 态

        预期：只有全0和全1，概率各50%
        """
        import random
        state = ghz["state_vector"]
        n = ghz["n_qubits"]
        dim = 2 ** n

        # 计算每个基态的概率
        probs = [abs(a) ** 2 for a in state]

        results = {}
        for _ in range(shots):
            r = random.random()
            cumulative = 0
            for i in range(dim):
                cumulative += probs[i]
                if r < cumulative:
                    key = f"|{i:0{n}b}⟩"
                    results[key] = results.get(key, 0) + 1
                    break

        sorted_results = dict(
            sorted(results.items(), key=lambda x: -x[1])
        )

        return {
            "n_qubits": n,
            "shots": shots,
            "results": sorted_results,
            "is_ghz": len(results) <= 2 and all(
                k in (f"|{0:0{n}b}⟩", f"|{dim-1:0{n}b}⟩") for k in results
            ),
        }

    @staticmethod
    def description(ghz: dict) -> str:
        """GHZ 态描述"""
        n = ghz["n_qubits"]
        state = ghz["state_vector"]
        dim = 2 ** n
        parts = []
        for i in range(dim):
            amp = state[i]
            if abs(amp) > 1e-10:
                label = f"|{i:0{n}b}⟩"
                if abs(amp - 1/math.sqrt(2)) < 0.01:
                    parts.append(label)
                elif abs(amp + 1/math.sqrt(2)) < 0.01:
                    parts.append(f"-{label}")
                else:
                    parts.append(f"{amp:.3f}{label}")
        return f"GHZ_{n} = ({' + '.join(parts)}) / √2"

    @staticmethod
    def draw_circuit(n: int) -> str:
        """绘制 GHZ 制备电路"""
        lines = []
        lines.append(f"  制备电路 (n={n}):")
        lines.append(f"  q0 |0⟩ ─ H ─ ● ─")
        for i in range(1, n):
            lines.append(f"  q{i} |0⟩ ───── ⊕ ─")
        return "\n".join(lines)


class WState:
    """W 态

    |W_n⟩ = (|100...0⟩ + |010...0⟩ + ... + |000...1⟩) / √n

    三 qubit W 态：
    |W_3⟩ = (|100⟩ + |010⟩ + |001⟩) / √3

    与 GHZ 的区别：
    - GHZ: 全 0 或全 1，二元结果
    - W: 恰好一个 1，均匀分布
    - W 态对 qubit 丢失更鲁棒
    """

    @staticmethod
    def create_3qubit() -> QuantumRegister:
        """制备 3-qubit W 态

        使用量子电路：
        1. Ry(θ1) on q0: 创建振幅比
        2. CNOT(q0, q1)
        3. Ry(θ2) on q1: 调整振幅
        4. CNOT(q1, q2)
        """
        reg = QuantumRegister(3, "w")

        # 近似 W 态制备
        # θ1 = 2 * arccos(1/√3)
        theta1 = 2 * math.acos(1 / math.sqrt(3))
        # 用 Hadamard + 相位调整近似
        reg.qubits[0] = QuantumGate.hadamard(reg.qubits[0])

        # CNOT
        reg.qubits[0], reg.qubits[1] = QuantumGate.cnot(
            reg.qubits[0], reg.qubits[1]
        )

        # 第二个 Hadamard
        reg.qubits[1] = QuantumGate.hadamard(reg.qubits[1])

        # CNOT
        reg.qubits[1], reg.qubits[2] = QuantumGate.cnot(
            reg.qubits[1], reg.qubits[2]
        )

        return reg

    @staticmethod
    def measure_all(reg: QuantumRegister, shots: int = 1000) -> dict:
        """多次测量统计"""
        results = {}
        n = reg.size

        for _ in range(shots):
            reg_copy = QuantumRegister(n, "m")
            for i in range(n):
                reg_copy.qubits[i] = QubitState(
                    alpha=reg.qubits[i].alpha,
                    beta=reg.qubits[i].beta,
                    label=reg.qubits[i].label,
                )

            bits = reg_copy.measure_all()
            key = "".join(str(b) for b in bits)
            results[key] = results.get(key, 0) + 1

        sorted_results = dict(
            sorted(results.items(), key=lambda x: -x[1])
        )

        return {
            "n_qubits": n,
            "shots": shots,
            "results": sorted_results,
        }


def multi_qubit_entanglement_demo():
    """多比特纠缠演示"""
    output = []

    output.append("=" * 60)
    output.append("🔗 多比特纠缠态演示")
    output.append("=" * 60)

    # 1. Bell 态回顾
    output.append("\n1️⃣  Bell 态 (2 qubits)")
    output.append("─" * 40)
    for bell in ["Φ+", "Φ-", "Ψ+", "Ψ-"]:
        pair = EntanglementChamber.create_bell_pair(bell)
        output.append(f"  {pair.description()}")

    # 2. GHZ 态
    output.append(f"\n2️⃣  GHZ 态 (3 qubits)")
    output.append("─" * 40)
    output.append(GHZState.draw_circuit(3))
    output.append("")

    ghz3 = GHZState.create_3qubit()
    output.append(GHZState.description(ghz3))
    output.append("")

    ghz3_result = GHZState.measure(ghz3, 1000)
    output.append(f"  测量 1000 次:")
    for state, count in ghz3_result["results"].items():
        bar = "█" * (count // 20)
        output.append(f"    {state}: {bar} {count} ({count/10:.1f}%)")
    output.append(f"  是 GHZ 态: {'✅' if ghz3_result['is_ghz'] else '❌'}")

    # 3. 4-qubit GHZ
    output.append(f"\n3️⃣  4-qubit GHZ 态")
    output.append("─" * 40)
    ghz4 = GHZState.create_nqubit(4)
    ghz4_result = GHZState.measure(ghz4, 1000)
    output.append(f"  测量 1000 次:")
    for state, count in ghz4_result["results"].items():
        bar = "█" * (count // 20)
        output.append(f"    {state}: {bar} {count} ({count/10:.1f}%)")
    output.append(f"  是 GHZ 态: {'✅' if ghz4_result['is_ghz'] else '❌'}")

    # 4. W 态
    output.append(f"\n4️⃣  W 态 (3 qubits)")
    output.append("─" * 40)
    w3 = WState.create_3qubit()
    w3_result = WState.measure_all(w3, 1000)
    output.append(f"  测量 1000 次:")
    for state, count in w3_result["results"].items():
        if count > 10:  # 只显示有意义的结果
            bar = "█" * (count // 20)
            output.append(f"    |{state}⟩: {bar} {count} ({count/10:.1f}%)")

    # 5. GHZ vs W 对比
    output.append(f"\n5️⃣  GHZ vs W 对比")
    output.append("─" * 40)
    output.append("  ┌──────────┬──────────────┬──────────────┐")
    output.append("  │          │   GHZ 态     │    W 态      │")
    output.append("  ├──────────┼──────────────┼──────────────┤")
    output.append("  │ 测量结果 │ 全0 或 全1   │ 恰好一个1   │")
    output.append("  │ 关联性   │ 完全关联     │ 完全反关联   │")
    output.append("  │ 鲁棒性   │ qubit丢失崩塌│ qubit丢失鲁棒│")
    output.append("  │ 用途     │ 密钥分发     │ 量子通信     │")
    output.append("  └──────────┴──────────────┴──────────────┘")

    return "\n".join(output)
