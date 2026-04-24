# CHANGELOG v1.6 — 官员晋升科举制 / Imperial Examination for Official Promotion

## 📌 Tag: v1.6
## 📅 2026-04-25
## 🏷️ Name: v1.6 AiAgent 帝国架构官员晋升科举制 Empire-Architecture

---

## 🎯 核心改进

### 1. 🔀 丞相并行分发 + 超时保护
- 丞相调度时自动并行分发所有任务（`asyncio.gather`）
- 每个节点独立超时保护（默认 60s），单节点卡死不影响全局
- 丞相规划和汇总也加了超时（45s）
- 支持在 `config.json` 中配置 `v16_features.node_timeout_seconds`

### 2. 📚 查曹自动触发知识路由
- 查曹（executor_researcher）在处理任务时**自动检索知识**
- 丞相在分发任务给查曹时，自动从指令和任务描述中提取关键词
- 知识检索结果作为上下文注入到查曹的 prompt 中
- 支持多关键词检索 + 结果合并去重
- 查曹输出带 📚 标记，表明是否使用了知识检索

### 3. 🔄 节点超时 + 失败重试
- `Agent.call_llm()` 增加重试机制（默认 2 次，线性退避）
- `Agent.process_task()` 增加整体超时保护（默认 60s）
- 超时/失败计数：`state.tasks_failed` 字段
- 错误分类更清晰：`[TIMEOUT]` / `[ERROR]` 前缀
- 状态页可看到失败计数

### 4. 🎭 角色 Prompt 柔性化
- 所有节点 prompt 改为 **"擅长 + 可协助"** 双层结构
- 技术参谋不再拒绝非技术任务——用结构化思维协助
- 码曹不再拒绝非编码任务——想想能不能用代码辅助
- 查曹明确收到**"第一步先检索知识"**的核心指令
- 每个节点新增 `capabilities`（擅长）和 `assist_roles`（可协助）字段

### 5. 📜 科举制度 — 九品中正制
- 参考中国古代科举制 + 九品中正制，建立 Agent 晋升体系
- **替补池**：最多 1024 个候补 Agent，贡献算力即可参与竞争
- **官员名额**：最多 256 个正式职位，按九品中正制分级
- **九品官阶**：正一品（太师/太傅）→ 正九品（书吏/驿丞），共 163 个官位
- **科举考试**：资格考试（入品）+ 晋升考试（升品）+ 复查考试（降品风险）
- **翰林院进修**：科举未第的候补自动进入翰林院学习，达标后重新参加考试
- **AI 评审**：丞相 Agent 可参与考核评分，综合历史表现 + AI 判断
- **考核维度**：质量分(40%) + 速度分(20%) + 可靠性(25%) + 协作分(15%)
- 每次任务执行后自动评估节点表现，累积决定晋升资格
- 晋升条件：完成足够任务 + 距上次考试足够久 + 综合分达标

### 6. 🤝 去中心化 P2P 协作
- 节点间可直接通信，不必事事经过丞相
- `Agent.send_to_peer()` — 单向消息
- `Agent.request_from_peer()` — 请求-回复 RPC
- `Agent.listen_for_peers()` — 监听来自其他节点的消息
- `MessageBus` 新增 `MessageType.PEER` 消息类型
- 丞相执行完主任务后自动启动 P2P 补充阶段
- 预定义 3 组常用 peer 协作对：
  - 技术参谋 → 查曹（补充技术文档检索）
  - 谋略参谋 → 情报参谋（补充市场数据）
  - 文曹 → 谋略参谋（确认写作框架）

---

## 📂 文件变更

| 文件 | 变更 |
|------|------|
| `lite/agents/base.py` | **重写** — 超时重试、P2P 通信、知识检索、柔性角色 |
| `lite/chancellor.py` | **重写** — 并行分发、自动知识路由、P2P 补充阶段、超时保护 |
| `lite/main.py` | **更新** — v1.6 banner、capabilities/knowledge 命令、失败节点提示 |
| `lite/config.json` | **更新** — v1.6 角色 prompt、capabilities/assist_roles、v16_features 配置 |
| `lite/core/bus.py` | **更新** — 新增 `MessageType.PEER` |
| `lite/core/keju.py` | **新增** — 科举院：九品中正制 + 考试 + 晋升 + 翰林院进修 |
| `CHANGELOG-v1.6.md` | **新增** — v1.6 完整变更日志 |

---

## 📊 预期改进（vs v1.5）

| 指标 | v1.5 | v1.6（预期） | 变化 |
|------|------|-------------|------|
| 执行耗时 | 160.4s | ~110-130s | ↓19-31% |
| 知识层调用 | 0 次 | 自动触发 | 从摆设变有用 |
| 节点利用率 | 62.5% | 80-100% | 柔性调度 |
| 容错能力 | 无 | 超时+重试 | 系统可靠性 |
| 通信模式 | 星型(经丞相) | 星型+P2P | 延迟更低 |
| 考核机制 | 无 | 科举制+九品中正 | 激励晋升 |

---

## 🔧 运行方式

```bash
cd lite
export MIMO_API_KEY="your-key"
export MIMO_API_ENDPOINT="https://your-endpoint/v1"

# 交互模式
python3 main.py

# 单次执行
python3 main.py "分析中国AI芯片产业的竞争格局"

# 查看节点能力画像
python3 main.py --capabilities

# 查看知识层状态
python3 main.py --knowledge

# 查看科举系统
python3 main.py --keju

# 科举子命令（交互模式）
keju               # 科举总览
keju officials     # 查看所有官员
keju reserves      # 查看替补池
keju training      # 翰林院进修
keju exam          # 举行科举考试
keju register <名> # 注册候补
keju top           # 排行榜
keju ranks         # 官阶分布
keju positions     # 官位状态
```

---

## 下一步

- 配置 1-2 个知识源凭据（如 Notion），验证知识注入闭环
- 收集 v1.6 实战数据，对比 v1.5 评估报告
- 注册候补候选人，首次运行科举考试
- 考虑引入强化学习调度器替代规则调度
