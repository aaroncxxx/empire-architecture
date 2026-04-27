# CHANGELOG

## v2.0.1 (优化版)

- **chancellor.py 重构**:
  - JSON 解析器重写：支持直接解析、代码块提取、花括号深度匹配三种策略
  - 知识层集成：初始化时自动挂载知识源，任务执行前自动预检索
  - 智能 fallback：根据任务关键词自动选择节点组合（写作/编码/检索/安全/翻译等）
  - 知识审计：记录每次知识检索请求
- **core/tokens.py 修复**:
  - `get_total_today` 改为从 `token_usage` 表按今日时间戳统计，修复计数器归零问题
  - `log_usage` 增加 `INSERT OR IGNORE` 确保 budget 行存在
  - 自动跨日重置：检测 `last_reset` 日期，新日自动清零
  - `check_budget` 增加跨日重置逻辑
- **main.py 增强**:
  - 新增 `knowledge` 命令查看知识层状态
  - 新增 `--knowledge` 启动参数
  - 任务输出显示知识层注入状态
  - Banner 更新为 v2.0
- **agents/base.py 优化**:
  - 知识上下文注入提示优化（"背景知识（仅供参考，基于检索自动注入）"）
- **v14_runner.py 修复**:
  - 路径改为相对路径，修复目录名变更后无法运行的问题

## v2.0.0 (归一版)

- 版本号收敛: v1.x → v2.0
- 文件结构重组:
  - `empire-architecture/` → `lite/`
  - changelog 合并: `docs/CHANGELOG-legacy.md`
  - `memory/` 移除
  - `skills/` 移除
  - 旧文档归档至 `docs/`
- 架构图新增
- SKILL.md 重写
- 代码不变

---

历史变更记录见 `docs/CHANGELOG-legacy.md`
