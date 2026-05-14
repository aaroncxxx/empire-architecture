"""量子比特 (Qubit) 模拟

用复数振幅精确模拟量子态：
  |0⟩ = [1, 0]
  |1⟩ = [0, 1]
  |+⟩ = [1/√2, 1/√2]  (叠加态)

核心原理：
- 量子态用二维复向量表示
- 测量导致波函数坍缩
- 不可克隆定理：无法完美复制未知量子态
"""
import math
import random
import cmath
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QubitState:
    """量子态：α|0⟩ + β|1⟩"""
    alpha: complex  # |0⟩ 振幅
    beta: complex   # |1⟩ 振幅
    label: str = ""  # 标签（如 "q0", "q1"）

    def probability_0(self) -> float:
        """测量得到 |0⟩ 的概率"""
        return abs(self.alpha) ** 2

    def probability_1(self) -> float:
        """测量得到 |1⟩ 的概率"""
        return abs(self.beta) ** 2

    def is_normalized(self) -> bool:
        """检查是否归一化"""
        total = self.probability_0() + self.probability_1()
        return abs(total - 1.0) < 1e-10

    def normalize(self):
        """归一化"""
        norm = math.sqrt(self.probability_0() + self.probability_1())
        if norm > 0:
            self.alpha /= norm
            self.beta /= norm

    def is_superposition(self) -> bool:
        """是否处于叠加态（非 |0⟩ 非 |1⟩）"""
        p0, p1 = self.probability_0(), self.probability_1()
        return p0 > 1e-10 and p1 > 1e-10

    def description(self) -> str:
        """人类可读的量子态描述"""
        p0, p1 = self.probability_0(), self.probability_1()

        if p0 > 0.999:
            return "|0⟩ (基态)"
        if p1 > 0.999:
            return "|1⟩ (激发态)"

        # 构建数学表达式
        parts = []
        if abs(self.alpha) > 1e-10:
            if abs(self.alpha - 1/math.sqrt(2)) < 0.01:
                parts.append("|0⟩")
            elif abs(self.alpha + 1/math.sqrt(2)) < 0.01:
                parts.append("-|0⟩")
            else:
                parts.append(f"{self.alpha:.3f}|0⟩")
        if abs(self.beta) > 1e-10:
            sign = "+" if self.beta.real >= 0 or abs(self.beta.real) < 1e-10 else ""
            if abs(abs(self.beta) - 1/math.sqrt(2)) < 0.01:
                parts.append(f"{sign}|1⟩")
            else:
                parts.append(f"{sign}{self.beta:.3f}|1⟩")

        math_str = " ".join(parts) if parts else "0"
        info = f"P(0)={p0:.1%}, P(1)={p1:.1%}"

        if self.is_superposition():
            return f"🔮 叠加态: {math_str}  [{info}]"
        return f"📊 {math_str}  [{info}]"

    def __repr__(self):
        return f"Qubit({self.label}: α={self.alpha:.4f}, β={self.beta:.4f})"


class Qubit:
    """量子比特"""

    @staticmethod
    def zero(label: str = "q0") -> QubitState:
        """创建 |0⟩ 态"""
        return QubitState(alpha=complex(1, 0), beta=complex(0, 0), label=label)

    @staticmethod
    def one(label: str = "q0") -> QubitState:
        """创建 |1⟩ 态"""
        return QubitState(alpha=complex(0, 0), beta=complex(1, 0), label=label)

    @staticmethod
    def plus(label: str = "q0") -> QubitState:
        """创建 |+⟩ = (|0⟩+|1⟩)/√2"""
        v = 1 / math.sqrt(2)
        return QubitState(alpha=complex(v, 0), beta=complex(v, 0), label=label)

    @staticmethod
    def minus(label: str = "q0") -> QubitState:
        """创建 |-⟩ = (|0⟩-|1⟩)/√2"""
        v = 1 / math.sqrt(2)
        return QubitState(alpha=complex(v, 0), beta=complex(-v, 0), label=label)

    @staticmethod
    def random(label: str = "q0") -> QubitState:
        """创建随机量子态"""
        theta = random.uniform(0, math.pi)
        phi = random.uniform(0, 2 * math.pi)
        alpha = complex(math.cos(theta / 2), 0)
        beta = complex(math.sin(theta / 2) * math.cos(phi),
                       math.sin(theta / 2) * math.sin(phi))
        return QubitState(alpha=alpha, beta=beta, label=label)

    @staticmethod
    def measure(state: QubitState) -> int:
        """测量量子态，返回 0 或 1"""
        p0 = state.probability_0()
        return 0 if random.random() < p0 else 1

    @staticmethod
    def measure_with_collapse(state: QubitState) -> tuple[int, QubitState]:
        """测量并返回坍缩后的状态"""
        result = Qubit.measure(state)
        if result == 0:
            collapsed = QubitState(alpha=complex(1, 0), beta=complex(0, 0), label=state.label)
        else:
            collapsed = QubitState(alpha=complex(0, 0), beta=complex(1, 0), label=state.label)
        return result, collapsed


class QuantumRegister:
    """量子寄存器：管理多个量子比特"""

    def __init__(self, size: int, prefix: str = "q"):
        self.qubits: list[QubitState] = [
            Qubit.zero(f"{prefix}{i}") for i in range(size)
        ]
        self.size = size
        self.measurements: list[tuple[str, int]] = []  # (label, result)

    def hadamard(self, index: int):
        """对指定比特施加 Hadamard 门"""
        if 0 <= index < self.size:
            from .gates import QuantumGate
            self.qubits[index] = QuantumGate.hadamard(self.qubits[index])

    def pauli_x(self, index: int):
        """对指定比特施加 Pauli-X 门"""
        if 0 <= index < self.size:
            from .gates import QuantumGate
            self.qubits[index] = QuantumGate.pauli_x(self.qubits[index])

    def measure_all(self) -> list[int]:
        """测量所有比特"""
        results = []
        for q in self.qubits:
            r = Qubit.measure(q)
            self.measurements.append((q.label, r))
            results.append(r)
        return results

    def state_vector(self) -> list[tuple[str, complex]]:
        """获取状态向量描述"""
        result = []
        for q in self.qubits:
            result.append((q.label, q.alpha, q.beta))
        return result

    def description(self) -> str:
        """人类可读的寄存器状态"""
        lines = [f"📦 量子寄存器 ({self.size} qubits)"]
        for q in self.qubits:
            lines.append(f"  {q.label}: {q.description()}")
        return "\n".join(lines)
