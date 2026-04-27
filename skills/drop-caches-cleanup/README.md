# 一键清理内存 (drop_caches) / One-Click Memory Cleanup

[中文](#中文) | [English](#english)

---

<a id="中文"></a>

## 中文

### 简介

一键清理系统内存（Linux Page Cache / macOS purge），立即释放物理内存。

### 功能

- 📊 清理前显示内存状态
- 🧹 支持 Linux `drop_caches` + macOS `purge`
- 🔀 分级清理（level 1/2/3）
- 🎯 阈值检查（低于阈值自动跳过）
- 🔍 Dry-run 模式（只看不做）
- ✅ 清理后自动评估内存状态
- 📋 JSON 结构化输出

### 使用方法

```bash
bash scripts/cleanup.sh [--level 1|2|3] [--threshold <pct>] [--dry-run] [--json]
```

或在 OpenClaw 中直接说：

> "清理内存" / "一键清理" / "内存太高了"

### 输出示例

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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 注意事项

- ⚠️ Linux 需要 root/sudo 权限
- ⚠️ macOS 需安装 Xcode CLI tools
- ✅ 只清理缓存（安全操作，不影响数据）

### 版本

**V1.2.0** - 2026-04-27

---

<a id="english"></a>

## English

### Overview

One-click system memory cleanup (Linux Page Cache / macOS purge) to instantly free physical RAM.

### Features

- 📊 Show memory status before cleanup
- 🧹 Linux `drop_caches` + macOS `purge` support
- 🔀 Granular cleanup levels (1/2/3)
- 🎯 Threshold check (skip when memory is fine)
- 🔍 Dry-run mode (view only)
- ✅ Post-cleanup assessment
- 📋 JSON structured output

### Usage

```bash
bash scripts/cleanup.sh [--level 1|2|3] [--threshold <pct>] [--dry-run] [--json]
```

Or in OpenClaw, just say:

> "clear memory" / "free memory" / "system lag"

### Example Output

```
⚡ Drop Caches Cleanup v1.2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖥️  Platform: Linux | Level: 3
📊 Before:
   Total: 3499MB | Used: 2788MB | Available: 711MB | Free: 150MB

🧹 Clearing (level 3)...

📊 After:
   Total: 3499MB | Used: 1988MB | Available: 1511MB | Free: 950MB

🎉 Successfully freed 800MB!
✅ Memory healthy (56%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Notes

- ⚠️ Linux requires root/sudo privileges
- ⚠️ macOS requires Xcode CLI tools
- ✅ Only clears caches (safe, no data loss)

### Version

**V1.2.0** - 2026-04-27

---

## License

MIT
