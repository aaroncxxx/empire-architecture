# 帝国架构 / Empire Architecture

基于中国古代三公九卿制的 AI 多智能体协作系统。

A multi-agent AI collaboration system inspired by China's Three Departments and Nine Ministries.

---

## 版本 / Versions

| 版本 | 说明 | 状态 |
|------|------|------|
| [v1 完整版](./empire-architecture-v1.md) | 41节点 + 联邦学习 + 投票制 | 设计文档 |
| [v1.1 精简版](./lite/) | 8节点 + 零依赖 + 可运行 | ✅ 可用 |
| [v1.3 知识增强](./lite/knowledge/) | 翰林院 + 四大知识源 + 审计 | ✅ 可用 |

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

## v1.3 知识增强版 / Knowledge Enhancement

详见 [lite/knowledge/](./lite/knowledge/)

### 翰林院 / Hanlin Academy

新增知识管理层，基于中国古代翰林院制度。

| 角色 | 人数 | 职能 |
|------|------|------|
| 翰林院祭酒 | 1 | 统筹调度，跨源检索，统一索引 |
| 腾讯云大学士 | 1 | 管理腾讯云知识引擎 |
| 飞书大学士 | 1 | 管理飞书知识库 |
| Notion大学士 | 1 | 管理 Notion 知识库 |
| 本地RAG大学士 | 1 | 管理本地向量库 |

### 四大知识源 / Four Knowledge Sources

| 知识源 | 说明 | 依赖 |
|--------|------|------|
| 腾讯云知识引擎 | 语义/全文/混合检索 | SecretId + SecretKey |
| 飞书知识库 | Wiki 节点搜索 | AppID + AppSecret |
| Notion | 全局/数据库检索 | Integration Token |
| 本地 RAG | TF-IDF 向量检索，零依赖 | 无 |

### 知识审计 / Knowledge Audit

- 记录每次知识检索（谁、查了什么、哪个源、多少 token）
- 每 2 小时自动出审计报表
- 支持 JSON 导出

### 快速启用 / Quick Start

```python
# 在 chancellor.py 中添加两行
from knowledge.mount import mount_knowledge
mount_knowledge(self)

# 启用知识源：编辑 lite/knowledge/config.py
# 填入凭据，enabled 改 True
```

### 本地 RAG 使用 / Local RAG Usage

```python
from knowledge.local_rag import LocalRAGKnowledge

rag = LocalRAGKnowledge()
rag.ingest_url("https://example.com/article")   # 抓取网页
rag.ingest_file("doc.md")                        # 导入文件
rag.ingest_directory("./docs/")                   # 批量导入
rag.ingest_text("标题", "内容")                   # 直接写入

results = await rag.search("查询内容", top_k=3)
```

## 节点总数 / Total Nodes

| 版本 | 节点数 | 人类 |
|------|--------|------|
| v1 完整版 | 41 AI + 1 皇帝 | 1 |
| v1.1 精简版 | 8 AI | 1 |
| v1.3 知识增强 | 8 AI + 4 知识管理 | 1 |

## License

MIT
