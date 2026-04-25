---
name: how-much-token-did-this-chat-used
description: >-
  Track and display token usage for the current OpenClaw session and recent
  sessions, with cost estimation and remaining days projection. Auto-detects
  active model and matches billing rules dynamically. Shows: current session
  tokens, session cost, today's cumulative usage, last 10 session averages,
  Credit balance auto-calculated from cumulative sessions, and estimated
  remaining days. Use when the user asks about token consumption, cost, usage
  stats, "用了多少 token" / "token 用量" / "消耗了多少" / "最近十个chat" /
  "credit" / "余额" / "还能用几天" / "花费". Trigger on: token count, token
  usage, cost tracking, usage statistics, session stats, credit balance,
  daily usage summary, cost estimation, remaining days.
---

# How Much Token Did This Chat Used / Token 用量查询 v2.0

## 核心原则 / Core Principles

- **纯读取、无写入、声明清晰** — 所有数据查询时实时获取
- **动态识别模型** — 不写死模型列表，从 session_status 解析
- **Credit 自动计算** — 从 sessions_list 累计 totalTokens，不写死数字
- **精确计量** — 使用实际输入/输出比，不硬编码估算比例

## 数据源 / Data Sources

| 数据 | 工具 | 说明 |
|------|------|------|
| 当前会话 | `session_status` | tokens in/out、model、context、cache |
| 历史会话 | `sessions_list(limit=10)` | totalTokens、updatedAt |
| 成本计算 | `scripts/cost.py` | 动态匹配计费规则 |

## 工作流 / Workflow

### Step 1: 获取当前会话

Call `session_status` → 解析：
- `model`: 模型名（如 `xiaomi/mimo-v2.5-pro` → `mimo-v2.5-pro`）
- `tokens in/out`: 精确输入输出 tokens
- `cache`: 缓存命中率
- `context`: 上下文使用量 / 最大上下文

### Step 2: 获取历史会话 + 按日聚合

Call `sessions_list(limit=10)`:

1. **今日累计**：筛选 `updatedAt` 在今天（Asia/Shanghai 时区）的会话，累加 `totalTokens`
2. **近 10 会话平均**：所有返回会话的 `totalTokens` 之和 ÷ 会话数
3. **已用 Credit**：所有会话 `totalTokens` 之和（累计）
4. **今日会话数**：今天（Asia/Shanghai）的会话数量

### Step 3: 读取总 Credit 额度

从 `memory/mimo-credit.json` 读取 `totalCredits` 字段。

### Step 4: 运行成本计算

```bash
python3 <skill_dir>/scripts/cost.py \
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
  --session-count <today_session_count>
```

兼容旧格式（位置参数）：
```bash
python3 <skill_dir>/scripts/cost.py <input> <output> <total> <used> <credit> <avg> [model]
```

其他命令：
```bash
python3 <skill_dir>/scripts/cost.py --list-models   # 列出支持的模型费率
python3 <skill_dir>/scripts/cost.py --help           # 查看帮助
python3 <skill_dir>/scripts/cost.py ... --json       # JSON 格式输出
```

## 输出格式 / Output Format

```
📊 成本与额度报告
🧠 模型: mimo-v2.5-pro
━━━━━━━━━━━━━━━━━━━━━
🔹 当前会话
   📥 输入: X,XXX  📤 输出: X,XXX
   💾 缓存: XX%  📚 上下文: XXk/1.0m (X%)
   💰 费用: ¥X.XXXX

📅 今日累计 (N 会话): ¥X.XX (≈ XXX Credit)
📊 近 10 会话平均: XX,XXX tokens/会话

💳 Credit
   已用: XX,XXX / X,XXX,XXX (X.X%)
   ⏳ 预计可用: XX.X 天
━━━━━━━━━━━━━━━━━━━━━
```

## 计费规则 / Billing Rates

内置 `scripts/cost.py`，通过 `--list-models` 查看支持列表。

| 模型 | 输入/1k | 输出/1k |
|------|---------|---------|
| mimo-v2-pro | ¥0.002 | ¥0.004 |
| mimo-v2.5-pro | ¥0.002 | ¥0.004 |
| mimo-v2.5 | ¥0.002 | ¥0.004 |

未知模型自动 fallback 到默认费率（¥0.002 / ¥0.004）。

## 注意事项 / Notes

- Credit 已用 = 所有会话累计 totalTokens（自动计算，无需手动更新）
- 总额度需从 `memory/mimo-credit.json` 读取（仅存储 totalCredits）
- Token 单价为参考值，实际以服务商计费为准
- **费用计算使用实际输入/输出比**，不再硬编码 70/30
- 时区：Asia/Shanghai (UTC+8)

## 更新日志 / Changelog

### v2.0.0
- 🐛 **修复今日累计计算** — 按日期过滤会话，不再把所有会话 totalTokens 当今日用量
- 🐛 **修复 avg_daily** — 按日聚合后计算真实日均消耗
- ✅ 使用实际输入/输出比替代硬编码 70/30
- ✅ 新增 mimo-v2.5 系列模型费率
- ✅ 支持 `--cache-pct` / `--context` / `--context-max` / `--session-count` 参数
- ✅ 支持 `--json` JSON 格式输出
- ✅ 支持 `--list-models` 查看费率列表
- ✅ 改进参数校验和错误提示
- ✅ 兼容旧的位置参数格式
- ✅ 输出格式与文档对齐

### v1.4.0
- ✅ 新增模型成本自动换算
- ✅ 新增 MiMo Credit 额度监控
- ✅ 新增上下文占比、缓存命中率统计
- 🧹 轻量重构：纯读取无写入
