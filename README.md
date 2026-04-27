# Empire Architecture v2.0

基于中国古代三公九卿制的 AI 多智能体协作系统

## 快速开始

```bash
cd lite/
export MIMO_API_KEY="your-key"
export MIMO_API_ENDPOINT="your-endpoint"
python3 main.py
```

## 架构

25 节点核心 + 537 节点天文台集群，采用三公九卿制组织：

- 丞相协调 → 参谋分析 → 六部执行 → 翰林知识 → 锦衣卫安全
- 观星台集群：512 Agent / 64 计算单元
- 并行自检：6类15项，0.06s 完成

## 目录

```
├── lite/       # 可运行代码
├── docs/       # 文档归档
└── CHANGELOG.md
```

## 详细文档

- [架构设计](docs/architecture-v1.md)
- [评估报告](docs/evaluation-v1.4.md)
- [历史变更](docs/CHANGELOG-legacy.md)

## 技术栈

MiMo | LangGraph | Redis | RabbitMQ | Flower | Vault | Prometheus

## 链接

- GitLab: https://gitlab.scnet.cn:9002/space/aaroncxxx/Empire-Architecture
- ClawHub: https://clawhub.ai/aaroncxxx/empire-architecture

## License

MIT-0
