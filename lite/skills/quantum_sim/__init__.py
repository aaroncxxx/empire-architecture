"""量子计算思维模拟器 - Quantum Computing Thinking Simulator

基于帝国架构的多智能体协作模式，模拟量子计算核心概念：
- 叠加态 (Superposition)
- 纠缠 (Entanglement)
- 并行计算 (Parallel Computing)
- 时空复用 (Time-Space Multiplexing)

灵感来源：九章四号光量子计算原型机
"""
from .qubit import Qubit, QuantumRegister
from .gates import QuantumGate
from .entanglement import EntanglementChamber
from .timeslice import TimeSpaceMultiplexer
from .quantum_agent import QuantumAgent, QuantumSwarm

__version__ = "2.1.0"
__all__ = [
    "Qubit", "QuantumRegister", "QuantumGate",
    "EntanglementChamber", "TimeSpaceMultiplexer",
    "QuantumAgent", "QuantumSwarm",
]
