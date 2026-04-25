# Empire-Architecture v1.91

基于中国古代三公九卿制的 AI 多智能体协作系统 — 天文台专用版

## 项目结构

```
├── empire-architecture/    # 帝国架构核心代码
│   ├── lite/               # 可运行版本 (537节点)
│   │   ├── main.py         # CLI入口
│   │   ├── chancellor.py   # 丞相协调器
│   │   ├── v14_runner.py   # 知识层运行器
│   │   ├── selfcheck_v17.py # V1.7 并行自检框架
│   │   ├── config.json     # 帝国25节点配置
│   │   ├── agents/         # Agent基类
│   │   ├── core/           # 消息总线/Token/安全
│   │   ├── knowledge/      # 翰林院知识层
│   │   └── observatory/    # 观星台集群 (V1.91)
│   │       ├── config.json # 集群配置 (512 Agent / 64 单元)
│   │       └── runner.py   # 集群运行器
│   ├── EVALUATION-v1.4.md  # 评估报告
│   ├── CHANGELOG-v1.7.md   # V1.7 更新日志
│   ├── CHANGELOG-v1.8.md   # V1.8 更新日志
│   ├── CHANGELOG-v1.91.md  # V1.91 更新日志 (天文台专用)
│   └── empire-architecture-v1.md  # 完整设计文档
├── skills/                 # ClawHub技能包 (7个)
│   ├── agent-autonomy-kit
│   ├── agentic-workflow-automation
│   ├── ai-agent-helper
│   ├── automation-workflow-builder
│   ├── how-much-token-did-this-chat-used
│   ├── mimo-tts-asr-26-free
│   └── system-selfcheck
├── memory/                 # 记忆与日志
│   ├── 2026-04-25.md
│   ├── 2026-04-26.md
│   └── MEMORY.md
├── SKILL.md               # ClawHub 发布描述
└── README.md
```

## 537 节点架构

### 帝国原有 25 节点

| 类别 | 节点 | 职责 |
|------|------|------|
| 中枢 | 丞相 | 总协调 |
| 参谋 | 谋略/技术/情报 | 分析决策 |
| 执行 | 文曹/码曹/查曹 | 任务执行 |
| 六部 | 吏/户/礼/兵/刑/工 | 专项管理 |
| 翰林 | 翰林学士/国子监 | 知识管理 |
| 特殊 | 钦天监/太医/御厨/观星台 | 预警/诊断/清洗/深度观测 |
| 监察 | 御史大夫/中书令 | 质量/流程 |
| 扩展 | 大理寺/大鸿胪/少府 | 逻辑/翻译/创意 |
| 安全 | 锦衣卫 | 安全审计 |

### 观星台集群 512 Agent（V1.91 新增）

| 角色 | 数量 | 职能 |
|------|------|------|
| 数据解析 Agent | 256 | 原始信号解码、频谱分析、数据清洗 |
| 模式识别 Agent | 128 | 周期信号检测、异常模式识别、源分类 |
| 质量控制 Agent | 128 | 数据校验、交叉比对、质量评分 |

- 64 个计算单元，每单元 8 Agent（异构）+ 8 影子 Agent
- 昼夜错峰调度：白天清洗 ~100万token / 夜间计算 ~800万token
- 三级质量校验：单元内 → 跨单元 → 历史对照
- 影子 Agent 故障恢复：RTO < 50ms

## 运行

### 帝国原有系统
```bash
cd empire-architecture/lite
export MIMO_API_KEY="your-key"
export MIMO_API_ENDPOINT="https://your-endpoint/v1"
python3 v14_runner.py "你的指令"
```

### 观星台集群
```bash
cd empire-architecture/lite/observatory
python3 runner.py          # 自动检测昼夜阶段
python3 runner.py status   # 集群状态
python3 runner.py day      # 白天模式（数据清洗）
python3 runner.py night    # 夜间模式（密集计算）
python3 runner.py qc       # 质量校验
python3 runner.py failover # 故障恢复测试
python3 runner.py full     # 完整流程
```

## License

MIT
