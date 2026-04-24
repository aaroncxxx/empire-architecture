---
name: empire-architecture
description: >
  基于中国古代三公九卿制的 AI 多智能体协作系统。
  8 个核心 Agent 节点（丞相/三参谋/三曹/锦衣卫）+ 翰林院知识管理层（9 大学士）。
  支持皇帝审批机制、知识审计、本地 RAG。纯 Python，零外部依赖。
  A multi-agent AI collaboration system inspired by China's Three Departments and Nine Ministries.
---

# 帝国架构 Empire Architecture

基于中国古代三公九卿制的 AI 多智能体协作系统。

## When to Use

| Situation | Use this skill? |
|---|---|
| 复杂任务需要多 Agent 协作 | ✅ Yes |
| 需要角色分工（战略/技术/情报/执行） | ✅ Yes |
| 需要安全审计输出 | ✅ Yes |
| 需要知识库增强决策 | ✅ Yes |
| 简单单轮问答 | ❌ No |

## Quick Start

### v1.1 精简版（零依赖）

```bash
cd lite
export MIMO_API_KEY="your-key"
export MIMO_API_ENDPOINT="https://your-endpoint/v1"
python3 main.py              # 交互模式
python3 main.py "你的指令"    # 单次执行
python3 main.py --status     # 查看状态
```

### v1.4/v1.5 知识增强版

```bash
cd lite
export MIMO_API_KEY="your-key"
export MIMO_API_ENDPOINT="https://your-endpoint/v1"
python3 v14_runner.py "你的指令"
```

## Architecture

```
皇帝（人类用户）
  │
  ├─ 丞相（AI 总协调器）
  │     ├─ 谋略参谋 — 战略分析、风险评估
  │     ├─ 技术参谋 — 技术方案、架构设计
  │     ├─ 情报参谋 — 信息收集、数据分析
  │     ├─ 文曹 — 文档撰写、内容创作
  │     ├─ 码曹 — 代码开发、自动化工具
  │     ├─ 查曹 — 信息检索、事实核查
  │     └─ 锦衣卫 — 安全审计、合规检查
  │
  └─ 翰林院祭酒（知识管理总管）
        ├─ 腾讯云大学士
        ├─ 飞书大学士
        ├─ Notion 大学士
        ├─ 本地 RAG 大学士
        ├─ WaytoAGI 大学士
        ├─ DataWhale 大学士
        ├─ ModelScope 大学士
        └─ LiblibAI 大学士
```

## Version History

| Version | Feature | Status |
|---------|---------|--------|
| v1.0 | 41 nodes + federated learning (design doc) | 📄 Design |
| v1.1 | 8 nodes + zero dependencies + CLI | ✅ Runnable |
| v1.3 | Hanlin Academy + 4 knowledge sources | ✅ Runnable |
| v1.4 | Community knowledge + emperor approval | ✅ Runnable |
| v1.5 | Evaluation report + knowledge runner | ✅ Runnable |

## Requirements

- Python 3.10+
- MiMo API Key (or any OpenAI-compatible LLM API)
- Zero external Python dependencies (pure stdlib)

## License

MIT
