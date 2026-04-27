# 帝国架构 Empire Architecture v2.0

基于中国古代三公九卿制的 AI 多智能体协作系统

## 概述

帝国架构是一个多智能体协作系统，采用三公九卿制组织架构，将复杂任务分解为多个专业 Agent 协同完成。

### 核心架构

- **中枢**：丞相 — 总协调，任务分解与调度
- **参谋**：谋略/技术/情报 — 分析决策
- **执行**：文曹/码曹/查曹 — 任务执行
- **六部**：吏/户/礼/兵/刑/工 — 专项管理
- **翰林**：翰林学士/国子监 — 知识管理
- **特殊**：钦天监/太医/御厨 — 预警/诊断/清洗
- **监察**：御史大夫/中书令 — 质量/流程
- **扩展**：大理寺/大鸿胪/少府 — 逻辑/翻译/创意
- **安全**：锦衣卫 — 安全审计

### 运行版本

lite/ 目录包含可运行的 Python 实现（25节点核心 + 537节点天文台集群）。

## 快速开始

```bash
# 进入 lite 目录
cd lite/

# 配置 LLM 凭据
export MIMO_API_KEY="your-api-key"
export MIMO_API_ENDPOINT="your-endpoint"

# 运行主程序
python3 main.py

# 运行并行自检
python3 selfcheck_v17.py
```

## 配置

编辑 `lite/config.json` 配置帝国节点：

```json
{
  "agents": [...],
  "knowledge": {...},
  "security": {...}
}
```

## 知识层

支持多种知识源：
- 本地 RAG（local_rag）
- 腾讯云（tencent_cloud）
- 飞书（feishu）
- Notion（notion_kb）
- 社区知识库（community）

## 自检框架

V1.7 并行自检框架，6类15项检查，0.06s 完成：
- 网络连通性
- API 可用性
- 文件系统完整性
- 配置一致性
- Agent 状态
- 知识层健康度

## 安全机制

- 锦衣卫投票制
- 违规三级分类
- 制衡机制
- Token 管理：皇帝唯一所有权、吏曹执行分配

## 联邦学习

支持横向/纵向联邦：
- 参数聚合
- 安全多方计算
- Flower 框架集成

## 技术栈

| 层面 | 选型 |
|------|------|
| 模型 | MiMo（小米） |
| 编排 | LangGraph |
| 通信 | Redis + RabbitMQ |
| 联邦学习 | Flower |
| 安全 | Vault + TenSEAL |
| 监控 | Prometheus + Grafana |

## 文件结构

```
├── SKILL.md          # 本文件
├── README.md         # 项目说明
├── CHANGELOG.md      # 变更记录
├── docs/             # 文档归档
│   ├── CHANGELOG-legacy.md
│   ├── architecture-v1.md
│   └── evaluation-v1.4.md
└── lite/             # 可运行代码
    ├── main.py       # CLI 入口
    ├── chancellor.py # 丞相协调器
    ├── selfcheck_v17.py
    ├── config.json
    ├── agents/
    ├── core/
    ├── knowledge/
    └── observatory/
```

## 链接

- GitLab: (private)
- ClawHub: (private)
