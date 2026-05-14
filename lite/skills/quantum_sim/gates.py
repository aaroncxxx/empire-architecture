"""量子门 (Quantum Gates)

经典逻辑门操作 0/1 比特，量子门操作量子态的复数振幅。

核心量子门：
- Hadamard (H): 创建叠加态，|0⟩ → |+⟩
- Pauli-X: 量子 NOT 门，翻转 |0⟩ ↔ |1⟩
- Pauli-Z: 相位翻转
- CNOT: 受控非门，产生纠缠的关键
- CZ: 受控 Z 门
- Toffoli: 双受控非门

所有门操作都是酉变换 (Unitary)，保证量子态归一化。
"""
import math
import cmath
from .qubit import QubitState


class QuantumGate:
    """量子门集合"""

    @staticmethod
    def hadamard(q: QubitState) -> QubitState:
        """Hadamard 门：创建叠加态
        H|0⟩ = (|0⟩+|1⟩)/√2
        H|1⟩ = (|0⟩-|1⟩)/√2

        矩阵：1/√2 [[1, 1], [1, -1]]
        """
        v = 1 / math.sqrt(2)
        new_alpha = v * (q.alpha + q.beta)
        new_beta = v * (q.alpha - q.beta)
        return QubitState(alpha=new_alpha, beta=new_beta, label=q.label)

    @staticmethod
    def pauli_x(q: QubitState) -> QubitState:
        """Pauli-X 门：量子 NOT，翻转 |0⟩ ↔ |1⟩
        矩阵：[[0, 1], [1, 0]]
        """
        return QubitState(alpha=q.beta, beta=q.alpha, label=q.label)

    @staticmethod
    def pauli_y(q: QubitState) -> QubitState:
        """Pauli-Y 门
        矩阵：[[0, -i], [i, 0]]
        """
        new_alpha = -1j * q.beta
        new_beta = 1j * q.alpha
        return QubitState(alpha=new_alpha, beta=new_beta, label=q.label)

    @staticmethod
    def pauli_z(q: QubitState) -> QubitState:
        """Pauli-Z 门：相位翻转
        矩阵：[[1, 0], [0, -1]]
        """
        return QubitState(alpha=q.alpha, beta=-q.beta, label=q.label)

    @staticmethod
    def phase(q: QubitState, phi: float) -> QubitState:
        """相位门 R(φ)
        矩阵：[[1, 0], [0, e^(iφ)]]
        """
        new_beta = q.beta * cmath.exp(1j * phi)
        return QubitState(alpha=q.alpha, beta=new_beta, label=q.label)

    @staticmethod
    def sqrt_x(q: QubitState) -> QubitState:
        """√X 门（平方根 NOT）
        矩阵：[[1+i, 1-i], [1-i, 1+i]] / 2
        """
        c = 0.5
        new_alpha = c * ((1+1j) * q.alpha + (1-1j) * q.beta)
        new_beta = c * ((1-1j) * q.alpha + (1+1j) * q.beta)
        return QubitState(alpha=new_alpha, beta=new_beta, label=q.label)

    @staticmethod
    def cnot(control: QubitState, target: QubitState) -> tuple[QubitState, QubitState]:
        """CNOT 门（受控非门）
        当 control=|1⟩ 时翻转 target

        |00⟩ → |00⟩
        |01⟩ → |01⟩
        |10⟩ → |11⟩
        |11⟩ → |10⟩

        这是产生量子纠缠的关键门。
        """
        p0 = control.probability_0()
        p1 = control.probability_1()

        # |0⟩ 分量：target 不变
        # |1⟩ 分量：target 翻转
        new_ctrl_alpha = control.alpha
        new_ctrl_beta = control.beta
        new_tgt_alpha = p0 * target.alpha + p1 * target.beta
        new_tgt_beta = p0 * target.beta + p1 * target.alpha

        return (
            QubitState(alpha=new_ctrl_alpha, beta=new_ctrl_beta, label=control.label),
            QubitState(alpha=new_tgt_alpha, beta=new_tgt_beta, label=target.label),
        )

    @staticmethod
    def toffoli(q1: QubitState, q2: QubitState, target: QubitState
                ) -> tuple[QubitState, QubitState, QubitState]:
        """Toffoli 门（双受控非门）
        当 q1=|1⟩ 且 q2=|1⟩ 时翻转 target
        """
        p11 = abs(q1.beta) ** 2 * abs(q2.beta) ** 2
        p10 = abs(q1.beta) ** 2 * abs(q2.alpha) ** 2
        p01 = abs(q1.alpha) ** 2 * abs(q2.beta) ** 2
        p00 = abs(q1.alpha) ** 2 * abs(q2.alpha) ** 2

        # 简化实现：只在两控制比特都为 |1⟩ 时翻转目标
        new_tgt_alpha = target.alpha
        new_tgt_beta = target.beta

        # |11⟩ 分量翻转 target
        flip_factor = p11
        new_tgt_alpha = target.alpha * (1 - flip_factor) + target.beta * flip_factor
        new_tgt_beta = target.beta * (1 - flip_factor) + target.alpha * flip_factor

        return (q1, q2, QubitState(alpha=new_tgt_alpha, beta=new_tgt_beta, label=target.label))

    @staticmethod
    def swap(q1: QubitState, q2: QubitState) -> tuple[QubitState, QubitState]:
        """SWAP 门：交换两个量子比特的状态"""
        return (
            QubitState(alpha=q2.alpha, beta=q2.beta, label=q1.label),
            QubitState(alpha=q1.alpha, beta=q1.beta, label=q2.label),
        )


class CircuitVisualizer:
    """量子线路可视化（ASCII）"""

    @staticmethod
    def draw_simple(gates: list[tuple[str, list[int]]], n_qubits: int) -> str:
        """绘制简单量子线路

        gates: [(gate_name, [target_qubits])]
        """
        lines = []
        for i in range(n_qubits):
            line = f"q{i} |0⟩ ──"
            for gate_name, targets in gates:
                if i in targets:
                    if gate_name == "H":
                        line += "[H]──"
                    elif gate_name == "X":
                        line += "[X]──"
                    elif gate_name == "M":
                        line += "[M]──"
                    else:
                        line += f"[{gate_name}]─"
                else:
                    line += "──────"
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def draw_cnot(control_idx: int, target_idx: int, n_qubits: int) -> str:
        """绘制 CNOT 门"""
        lines = []
        for i in range(n_qubits):
            if i == min(control_idx, target_idx):
                line = f"q{i} |0⟩ ──●──"
            elif i == max(control_idx, target_idx):
                line = f"q{i} |0⟩ ──⊕──"
            else:
                line = f"q{i} |0⟩ ─────"
            lines.append(line)
        return "\n".join(lines)
