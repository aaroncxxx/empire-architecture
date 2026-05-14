---
name: quantum-computing-simulator
description: 量子计算思维模拟器 — 基于帝国架构的多智能体量子协作演示。直观理解叠加态、纠缠、并行计算和时空复用。灵感来自九章四号光量子计算原型机。
metadata:
  {
    "openclaw":
      {
        "version": "2.1.0",
        "author": "aaroncxxx",
        "tags": ["quantum", "simulation", "multi-agent", "education", "empire-architecture"],
      },
  }
---

# 量子计算思维模拟器 v2.1

Quantum Computing Thinking Simulator

## 概述

基于帝国架构的多智能体协作模式，直观演示量子计算核心概念。让普通用户无需数学背景也能理解量子计算的精髓。

灵感来源：九章四号光量子计算原型机

## 核心概念

| 量子概念 | 帝国架构对应 | 用户体验 |
|---------|-------------|---------|
| 叠加态 | Agent 同时持有多个观点 | Agent 有多种可能立场，概率可视化 |
| 纠缠 | Agent 间深度协作关联 | 一个 Agent 确定，另一个自动关联 |
| 测量坍缩 | 确定立场/选择方案 | 叠加态变为确定结果 |
| 时空复用 | 同一 Agent 多角色轮转 | 九章四号风格的调度演示 |
| 量子行走 | 决策空间多路径探索 | 同时探索多条路径 |
| Bell 不等式 | 协作有效性验证 | 验证量子非局域性 |

## 快速开始

```bash
# 交互模式
python3 quantum_cli.py

# 完整演示
python3 quantum_cli.py demo

# 单独实验
python3 quantum_cli.py superposition  # 叠加态
python3 quantum_cli.py entangle       # 纠缠
python3 quantum_cli.py timeslice      # 时空复用
python3 quantum_cli.py debate         # 量子辩论
python3 quantum_cli.py bell           # Bell 不等式
python3 quantum_cli.py walk           # 量子行走
python3 quantum_cli.py network        # 纠缠网络
```

## 作为 Skill 使用

```python
from skills.quantum_sim import Qubit, QuantumGate, EntanglementChamber
from skills.quantum_sim import QuantumAgent, QuantumSwarm
from skills.quantum_sim import TimeSpaceMultiplexer

# 创建叠加态
q = Qubit.zero()
q = QuantumGate.hadamard(q)  # |0⟩ → |+⟩
print(q.description())

# 创建纠缠对
pair = EntanglementChamber.create_bell_pair("Φ+")
ra, rb = EntanglementChamber.measure_pair(pair)

# 量子辩论
agent_a = QuantumAgent("A", "参谋A")
agent_b = QuantumAgent("B", "参谋B")
debate = agent_a.quantum_debate(agent_b, "议题", rounds=3)
```

## 文件结构

```
quantum_sim/
├── __init__.py         # 包入口
├── qubit.py            # 量子比特模拟
├── gates.py            # 量子门集合
├── entanglement.py     # 纠缠对与 Bell 态
├── timeslice.py        # 时空复用器
├── quantum_agent.py    # 量子智能体
└── quantum_cli.py      # CLI 入口
```

## 技术栈

- Python 3.8+
- 纯 Python 实现（无外部依赖）
- 复数振幅精确模拟
- ASCII 可视化

## 链接

- GitHub: https://github.com/aaroncxxx/empire-architecture
- 灵感: 九章四号光量子计算原型机
