---
name: system-selfcheck
description: >
  系统自检：一键诊断 OpenClaw 运行环境，输出结构化报告。
  检查系统资源、运行时依赖、网络连通性、API 配置、Skills 状态。
  预留 MiClaw / Hermes 平台适配。
applyTo: "**"
---

# 系统自检 System Self-Check

一键诊断 Agent 运行环境，输出结构化健康报告。

> **关于作者** — 十五年老米粉了！！冲！！！
>
> **功能清单：**
> - ✅ 系统/内存/磁盘/CPU 检查
> - ✅ Python/Node/ffmpeg/jq 依赖检测
> - ✅ GitHub/MiMo API/ClawHub 网络连通性
> - ✅ OpenClaw Gateway/Config/Skills/API Keys
> - ✅ `--brief` 精简 / `--json` 结构化 / `--fix` 自动修复
> - ✅ 预留 MiClaw/Hermes 平台入口
> - ✅ 告警阈值（内存 ⚠️<30% 🔴<10%，磁盘同理，网络 ⚠️>3s 🔴超时）

## When to Use

| Situation | Use this skill? |
|---|---|
| 用户说"系统自检" / "健康检查" / "status check" / "diagnostics" | ✅ Yes |
| 排查环境问题（依赖缺失、网络不通、配置错误） | ✅ Yes |
| 定期巡检（配合 cron 定时执行） | ✅ Yes |
| 部署后验证环境是否就绪 | ✅ Yes |

## Usage

```bash
bash "{baseDir}/scripts/selfcheck.sh" [options]
```

### Options

| Flag | Description |
|------|-------------|
| `--brief` | 精简模式，只显示问题项 |
| `--json` | JSON 格式输出 |
| `--fix` | 自动修复可修复的问题（安装缺失依赖等） |
| `--platform <name>` | 强制指定平台：openclaw / miclaw / hermes（默认自动检测） |

### Examples

```bash
# 完整自检
bash "{baseDir}/scripts/selfcheck.sh"

# 只看问题
bash "{baseDir}/scripts/selfcheck.sh" --brief

# JSON 输出（方便程序消费）
bash "{baseDir}/scripts/selfcheck.sh" --json

# 自动修复
bash "{baseDir}/scripts/selfcheck.sh" --fix
```

## 检查项

### 通用检查（所有平台）

| 模块 | 检查内容 | 告警阈值 |
|------|---------|---------|
| 系统 | OS、内核、CPU 核数/架构、主机名 | — |
| 内存 | 总量/可用/百分比 | ⚠️ <30% 可用 / 🔴 <10% |
| 磁盘 | 总量/已用/可用 | ⚠️ <30% 可用 / 🔴 <10% |
| 运行时 | Python、Node 版本 | — |
| 核心依赖 | ffmpeg、jq、curl、git | 缺失即 🔴 |
| 网络 | GitHub、MiMo API、ClawHub 连通性 | ⚠️ >3s / 🔴 超时 |

### OpenClaw 专属检查

| 检查项 | 内容 |
|--------|------|
| Gateway | 运行状态 |
| 配置文件 | `~/.openclaw/openclaw.json` 完整性 |
| Skills | 已安装列表 + 缺失依赖 |
| API Keys | MIMO_API_KEY / ClawHub Token（仅检查存在，不输出值） |

### 预留平台（TODO）

- **MiClaw**：`check_miclaw.sh` — MiMo Agent 平台适配
- **Hermes**：`check_hermes.sh` — Hermes Agent 平台适配

## 输出格式

```
⚡ System Self-Check Report — OpenClaw
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Platform]  ✅ OpenClaw 2026.3.12
[System]    ✅ Linux 6.8.0 | Xeon × 2 | x86_64
[Memory]    ⚠️ 3.4G total / 2.4G available (71%)
[Disk]      ✅ 40G / 30G free (22%)
[Runtime]   ✅ Python 3.12.3 | Node v22.22.1
[Deps]      ✅ ffmpeg 6.1.1 | jq ✅ | ❌ gh CLI
[Network]   ✅ github.com 200 (1.2s)
[Network]   ✅ api.xiaomimimo.com 200 (0.3s)
[Skills]    ✅ 46 installed
[API Keys]  ✅ MIMO_API_KEY | ✅ ClawHub Token
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 15 passed | 1 warning | 1 failed
```

## 定时自检（Cron）

通过 OpenClaw cron 定期执行：

```
schedule: "0 9 * * *"   # 每天早上 9 点
payload: "执行系统自检并报告异常"
```

## 交付格式

- 默认：直接回复结构化文本报告
- `--json`：回复 JSON 格式
- `--brief`：只回复问题项，无问题则回复 "All clear ✅"
