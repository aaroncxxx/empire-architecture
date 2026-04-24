# 帝国架构 / Empire Architecture

基于中国古代三公九卿制的 AI 多智能体协作系统。

A multi-agent AI collaboration system inspired by China's Three Departments and Nine Ministries.

---

## 版本 / Versions

| 版本 | 说明 | 状态 |
|------|------|------|
| [v1 完整版](./empire-architecture-v1.md) | 41节点 + 联邦学习 + 投票制 | 设计文档 |
| [v1.1 精简版](./lite/) | 8节点 + 零依赖 + 可运行 | ✅ 可用 |

## v1 完整版 / Full Architecture

详见 [empire-architecture-v1.md](./empire-architecture-v1.md)

- 41 个 AI 节点 + 1 个人类皇帝
- 三公九卿制完整映射
- 联邦学习（横向/纵向）
- 锦衣卫投票制处决
- 替补池自动补位
- 6小时/天会议体系

## v1.1 精简版 / Lite Version

详见 [lite/](./lite/)

- 8 个核心节点，可运行
- 零外部依赖（纯 Python）
- 异步消息总线 + SQLite Token 追踪
- 时间加速引擎（10x）
- MiMo V2.5 Pro 驱动

```bash
cd lite
python3 main.py              # 交互模式
python3 main.py "你的指令"    # 单次执行
```

## License

MIT
