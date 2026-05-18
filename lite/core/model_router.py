"""帝国架构 v2.9 - 模型路由器（大小模型分级）"""
from .logger import get_logger

log = get_logger("model_router")

# 模型配置
MODELS = {
    "large": {
        "name": "mimo-v2.5-pro",
        "max_tokens": 4096,
        "temperature": 0.7,
        "cost_per_1k": 0.05,
    },
    "small": {
        "name": "mimo-v2.5-pro",
        "max_tokens": 2048,
        "temperature": 0.5,
        "cost_per_1k": 0.01,
    },
}

# Agent 角色 → 模型映射
ROLE_MODEL_MAP = {
    # 丞相和参谋用大模型
    "丞相": "large",
    "三公": "large",
    "参谋·战略": "large",
    "参谋·技术": "large",
    "参谋·情报": "large",
    "参谋·创新": "large",
    "军师": "large",
    # 执行类用小模型
    "执行·写作": "small",
    "执行·编码": "small",
    "执行·翻译": "small",
    "执行·格式化": "small",
    "执行·摘要": "small",
    "执行·校验": "small",
    "执行·汇报": "small",
    "执行·归档": "small",
    # 监察用小模型
    "监察·廉政": "small",
    "监察·效能": "small",
    "监察·品质": "small",
    "监察·合规": "small",
    # 地方官用小模型
    "地方": "small",
    "郡守": "small",
}

# 关键词 → 模型映射（任务复杂度判断）
COMPLEXITY_KEYWORDS = {
    "large": ["战略", "架构", "设计", "分析", "规划", "评估", "决策", "创新", "研究"],
    "small": ["翻译", "格式", "摘要", "汇报", "检查", "校验", "归档", "列表", "统计"],
}


def select_model(agent_role: str, task_prompt: str = "") -> dict:
    """根据 Agent 角色和任务复杂度选择模型"""

    # 1. 按角色匹配
    for role_prefix, model_key in ROLE_MODEL_MAP.items():
        if role_prefix in agent_role:
            model = MODELS[model_key]
            log.debug(f"角色路由: {agent_role} → {model['name']}")
            return model

    # 2. 按任务关键词匹配
    task_lower = task_prompt.lower()
    for model_key, keywords in COMPLEXITY_KEYWORDS.items():
        if any(kw in task_lower for kw in keywords):
            model = MODELS[model_key]
            log.debug(f"关键词路由: {task_prompt[:20]}... → {model['name']}")
            return model

    # 3. 默认大模型
    return MODELS["large"]


def get_model_stats() -> dict:
    """获取模型配置信息"""
    return {
        key: {"name": m["name"], "cost": m["cost_per_1k"]}
        for key, m in MODELS.items()
    }
