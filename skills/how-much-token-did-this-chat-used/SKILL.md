---
name: how-much-token-did-this-chat-used
description: >-
  Track and display token usage for the current OpenClaw session and recent
  sessions, with cost estimation and remaining days projection. Auto-detects
  active model and matches billing rules dynamically. Shows: current session
  tokens, session cost, today's cumulative usage, last 10 session averages,
  7-day usage trend, top spending sessions, credit balance with alerts,
  and weighted remaining days projection.
  Use when the user asks about token consumption, cost, usage stats,
  "用了多少 token" / "token 用量" / "消耗了多少" / "最近十个chat" /
  "credit" / "余额" / "还能用几天" / "花费" / "趋势".
---

# Token 用量查询 v2.1

> **关于作者** — 十五年老米粉了！！冲！！！
> v2.1 优化：7天趋势图、费用告警、Top烧钱会话、加权剩余天数、JSON增强。

## 核心原则

- **纯读取、无写入** — 所有数据实时获取
- **动态识别模型** — 不写死模型列表，从 session_status 解析
- **Credit 自动计算** — 从 sessions_list 累计 totalTokens
- **精确计量** — 使用实际输入/输出比，不硬编码估算比例

## 数据源

| 数据 | 工具 | 说明 |
|------|------|------|
| 当前会话 | `session_status` | tokens in/out、model、context、cache |
| 历史会话 | `sessions_list(limit=10)` | totalTokens、updatedAt |
| 成本计算 | `scripts/cost.py` | 动态匹配计费规则 |

## 工作流

### Step 1: 获取当前会话

Call `session_status` → 解析 model、tokens in/out、cache、context。

### Step 2: 获取历史会话 + 按日聚合

Call `sessions_list(limit=10)`:
1. **今日累计**：筛选今天（Asia/Shanghai）的会话，累加 totalTokens
2. **近 10 会话平均**：所有会话 totalTokens 之和 ÷ 会话数
3. **近 7 天趋势**：按日聚合，生成每日 token 消耗数据
4. **Top 烧钱会话**：按 totalTokens 降序排列，取前 5

### Step 3: 运行成本计算

```bash
python3 "{baseDir}/scripts/cost.py" \
  --input <tokens_in> \
  --output <tokens_out> \
  --total <today_total_tokens> \
  --used <cumulative_used> \
  --credit <total_credit> \
  --avg <avg_daily_tokens> \
  --model <model_name> \
  --cache-pct <cache_hit_pct> \
  --context <context_tokens> \
  --context-max <max_context> \
  --session-count <today_session_count> \
  --daily '[["04-27",12400],["04-26",8200],...]' \
  --top-sessions '[["session-abc",12400,0.0372],...]' \
  --warn 80,95
```

其他命令：
```bash
python3 "{baseDir}/scripts/cost.py" --list-models
python3 "{baseDir}/scripts/cost.py" --help
python3 "{baseDir}/scripts/cost.py" ... --json
```

## 输出格式

```
📊 成本与额度报告
🧠 模型: mimo-v2.5-pro
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔹 当前会话
   📥 输入: 1,234  📤 输出: 567
   💾 缓存: 45%  📚 上下文: 12.5k/1.0m (1.2%)
   💰 费用: ¥0.0047
   ⚠️  Credit 使用率 82.3%，已超过 80% 阈值，请关注消耗速度

📅 今日累计 (3 会话): ¥0.0156 (≈ 4,200 Credit)
📊 近 10 会话平均: 5,600 tokens/会话

📈 近 5 天消耗趋势
   04-27  ████████████  12,400 tokens
   04-26  ███████░░░░░   8,200 tokens
   04-25  ████░░░░░░░░   4,100 tokens
   04-24  █████████░░░  10,300 tokens
   04-23  ██████░░░░░░   6,800 tokens

🔥 最近会话消耗 Top 3
   1. session-abc123…    12,400 tokens  ¥0.0372
   2. session-def456…     8,200 tokens  ¥0.0246
   3. session-ghi789…     4,100 tokens  ¥0.0123

💳 Credit
   已用: 456,789 / 555,555 (82.2%)
   ⏳ 预计可用: 8.3 天
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 新增功能

### 📈 7 天趋势图

从 sessions_list 按日聚合，文本柱状图展示消耗趋势。
- 只显示最近 7 天有数据的日期
- 自动缩放柱状图比例

### ⚠️ 费用告警

通过 `--warn 80,95` 设置阈值（默认 80% 和 95%）：
- **80%** → ⚠️ 警告："请关注消耗速度"
- **95%** → 🔴 严重："建议立即补充额度"

### 🔥 Top 烧钱会话

从 sessions_list 按 totalTokens 降序，展示前 5 名最烧钱会话。

### ⏳ 加权剩余天数

不再用简单平均，改为加权：
- 近 3 天权重 60%（近期行为更准）
- 近 7 天权重 30%
- 近 30 天权重 10%
- 不足时自动降级使用可用数据

## 计费规则

| 模型 | 输入/1k | 输出/1k |
|------|---------|---------|
| mimo-v2-pro | ¥0.002 | ¥0.004 |
| mimo-v2.5-pro | ¥0.002 | ¥0.004 |
| mimo-v2.5 | ¥0.002 | ¥0.004 |

未知模型自动 fallback 到默认费率。

## 注意事项

- Credit 已用 = 所有会话累计 totalTokens
- Token 单价为参考值，实际以服务商计费为准
- 费用计算使用实际输入/输出比
- 时区：Asia/Shanghai (UTC+8)

## 版本历史

### v2.1.0 (2026-04-27)

- 📈 新增近 7 天消耗趋势（文本柱状图）
- ⚠️ 新增费用告警阈值 `--warn`（默认 80%/95%）
- 🔥 新增 Top 烧钱会话分列
- ⏳ 剩余天数改为加权平均（近3天60% + 近7天30% + 近30天10%）
- 📋 JSON 增强：trend / top_sessions / alerts 字段
- 🎨 输出格式优化，信息密度提升

### v2.0.0 (2026-04-23)

- 🐛 修复今日累计计算（按日期过滤）
- 🐛 修复 avg_daily（按日聚合）
- ✅ 使用实际输入/输出比
- ✅ 新增 mimo-v2.5 系列费率
- ✅ 支持 --json / --list-models
