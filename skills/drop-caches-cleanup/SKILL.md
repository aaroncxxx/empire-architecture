---
name: drop-caches-cleanup
version: 1.2.0
description: >
  一键清理系统内存（RAM）/ One-click system memory cleanup.
  当用户说"清理内存"、"释放内存"、"一键清理"、"drop caches"、"内存太高"、"卡"、"慢"
  / "clear memory"、"free memory"、"memory cleanup"、"system lag" 时使用。
  支持 Linux drop_caches / macOS purge，分级清理，阈值检查。
---

# 一键清理内存 / One-Click Memory Cleanup

一键清理 Linux Page Cache 或 macOS 内存缓存，释放物理内存。
One-click cleanup of Linux Page Cache / macOS memory cache to free physical RAM.

> **关于作者** — 十五年老米粉了！！冲！！！v1.2 优化：分级清理、阈值检查、macOS 支持、内存计算修正。

## 使用方法 / Usage

```bash
bash "{baseDir}/scripts/cleanup.sh" [options]
```

### Options

| Flag | Description |
|------|-------------|
| `--level 1\|2\|3` | 清理级别：1=page cache, 2=dentries+inodes, 3=全部(默认) |
| `--threshold <pct>` | 内存使用率低于此值时跳过清理 (0-100) |
| `--dry-run` | 仅显示内存状态，不执行清理 |
| `--json` | JSON 格式输出 |
| `-h, --help` | 显示帮助 |

### Examples

```bash
# 基础清理（全部缓存）
bash "{baseDir}/scripts/cleanup.sh"

# 只清理 page cache
bash "{baseDir}/scripts/cleanup.sh" --level 1

# 内存使用率低于 70% 时跳过
bash "{baseDir}/scripts/cleanup.sh" --threshold 70

# 先看看状态，不执行
bash "{baseDir}/scripts/cleanup.sh" --dry-run

# JSON 输出（方便程序消费）
bash "{baseDir}/scripts/cleanup.sh" --json
```

## 功能 / Features

- ✅ Linux `drop_caches` + macOS `purge` 双平台支持
- ✅ 分级清理（level 1/2/3）
- ✅ 阈值检查（低于阈值自动跳过）
- ✅ Dry-run 模式（只看不做）
- ✅ 权限预检（不够直接报错）
- ✅ 内存计算修正（用 available 差值，非 used 差值）
- ✅ 清理后自动评估（✅良好 / ⚠️偏高 / 🔴危险）
- ✅ JSON 结构化输出
- ✅ 定时清理建议

## 清理级别说明

| Level | Linux | macOS |
|-------|-------|-------|
| 1 | Page Cache only | `purge`（整体清理） |
| 2 | dentries + inodes | `purge` |
| 3 | **全部（默认）** | `purge` |

> macOS 只有 `purge` 一个级别，`--level` 参数在 macOS 上不影响行为。

## 输出示例

```
⚡ Drop Caches Cleanup v1.2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖥️  平台: Linux | 清理级别: level 3
📊 清理前：
   总量: 3499MB | 已用: 2788MB | 可用: 711MB | 空闲: 150MB

🧹 正在清理 (level 3)...

📊 清理后：
   总量: 3499MB | 已用: 1988MB | 可用: 1511MB | 空闲: 950MB

🎉 成功释放 800MB 可用内存！
✅ 内存状态良好 (56%)

💡 如需定时清理，可配置 cron：
   0 */6 * * * /path/to/cleanup.sh --threshold 70
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 注意事项 / Notes

- ⚠️ Linux 需要 root/sudo 权限
- ⚠️ macOS 需安装 Xcode CLI tools（`xcode-select --install`）
- ✅ 只清理缓存（安全操作，不影响数据）
- ⏱️ 清理后可能需要几秒才能看到完整效果

## 定时清理（Cron）

```bash
# 每 6 小时检查一次，使用率超 70% 才清理
0 */6 * * * /path/to/cleanup.sh --threshold 70 --json >> /var/log/mem-cleanup.log
```

## 版本历史

### v1.2.0 (2026-04-27)

- 🔀 分级清理：`--level 1/2/3`，默认 level 3（全部）
- 🍎 macOS 支持：自动检测并使用 `purge` 命令
- 🎯 阈值检查：`--threshold` 低于阈值自动跳过
- 🔍 Dry-run：`--dry-run` 只看状态不执行
- 🔧 内存计算修正：用 `available` 差值替代 `used` 差值
- 🔒 权限预检：执行前检查 root/sudo
- 📊 清理后评估：✅/⚠️/🔴 三级评估
- 📋 JSON 输出：`--json` 结构化数据
- 💡 cron 建议：清理后提示定时清理配置

### v1.1.0 (2026-04-25)

- 🚀 首发：Linux Page Cache 一键清理，前后对比显示
