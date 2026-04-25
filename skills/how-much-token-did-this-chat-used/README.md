# How Much Token Did This Chat Used / Token 用量查询

> 🎉 v1.4.0 正式发布 — 更准、更全、更安全、更好用

## 功能一览 / Features

| 功能 | 说明 |
|------|------|
| 📊 Token 统计 | 输入/输出 tokens、缓存命中率、上下文占用 |
| 💰 成本估算 | 按模型费率自动计算本次/今日人民币花费 |
| 🤖 模型识别 | 自动检测 MiMo/GPT/Claude/豆包 等，匹配计费规则 |
| 📅 今日累计 | 当天所有会话 token 汇总 |
| 📚 近 10 会话 | 多会话平均长度 + 总计 |
| 💳 Credit 监控 | MiMo Credit 额度 + 剩余可用天数预估 |
| ⏳ 剩余天数 | 按日均消耗估算还能用几天 |

## 安全 / Security

- ✅ 全程只读不写，无越权行为
- ✅ 不读写本地敏感文件
- ✅ 符合 OpenClaw 安全规范

## 安装 / Install

```bash
clawhub install how-much-token-did-this-chat-used
# 或
skillhub install how-much-token-did-this-chat-used
```

## 触发词 / Triggers

- 用了多少 token / token 用量 / 消耗了多少
- credit 余额 / 还能用几天 / 花费
- 最近十个 chat / 今日消耗

## 更新日志 / Changelog

### v1.4.0
- ✅ 新增模型成本自动换算，直接显示人民币花费 / Auto cost with CNY
- ✅ 新增 MiMo Credit 额度监控 + 剩余可用天数预估 / Credit + remaining days
- ✅ 新增上下文占比、缓存命中率统计 / Context & cache hit rate
- ✅ 多模型自动识别，适配不同计费标准 / Multi-model auto-detect
- 🧹 轻量重构：纯读取无写入 / Read-only, no writes

### v1.3.0
- 🤖 自动识别模型 / Auto model detection
- 📅 今日累计消耗 / Today's cumulative
- 📊 近 10 会话平均 / Last 10 avg

### v1.2.0
- 💳 MiMo V2 Credit 余额 / Credit balance

### v1.1.0
- 📚 最近 10 会话合计 / Last 10 sessions

### v1.0.0
- 📊 基础 Token 统计 / Basic token tracking

## 链接 / Links

- ClawHub: https://clawhub.ai/aaroncxxx/how-much-token-did-this-chat-used
