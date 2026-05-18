"""帝国架构 v2.9 - 增强型配置"""
import json
import os
import time
import threading
from .logger import get_logger

log = get_logger("config")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
OPENCLAW_CONFIG = os.path.expanduser("~/.openclaw/openclaw.json")

# 全局配置缓存 + 热加载
_config_cache = None
_config_mtime = 0
_lock = threading.Lock()


def load_empire_config() -> dict:
    """加载配置（支持热加载：检测文件变更自动重载）"""
    global _config_cache, _config_mtime

    try:
        mtime = os.path.getmtime(CONFIG_PATH)
    except FileNotFoundError:
        log.error(f"配置文件不存在: {CONFIG_PATH}")
        return {"llm": {}, "agents": {}}

    with _lock:
        if _config_cache is not None and mtime == _config_mtime:
            return _config_cache

        with open(CONFIG_PATH, encoding="utf-8") as f:
            _config_cache = json.load(f)
        _config_mtime = mtime
        log.info(f"配置已加载/重载 (mtime={mtime})")
        return _config_cache


def invalidate_config_cache():
    """强制重载配置"""
    global _config_cache
    with _lock:
        _config_cache = None
    log.info("配置缓存已清除")


def load_llm_credentials():
    """从环境变量读取 LLM 凭据"""
    api_key = os.environ.get("MIMO_API_KEY", "")
    endpoint = os.environ.get("MIMO_API_ENDPOINT", "")
    if not api_key or not endpoint:
        try:
            with open(OPENCLAW_CONFIG) as f:
                oc = json.load(f)
            providers = oc.get("models", {}).get("providers", {})
            for name, p in providers.items():
                if "apiKey" in p:
                    api_key = api_key or p["apiKey"]
                    endpoint = endpoint or p.get("baseURL") or p.get("baseUrl", "")
        except Exception:
            pass
    if endpoint and not endpoint.endswith("/chat/completions"):
        endpoint = endpoint.rstrip("/") + "/chat/completions"
    return {
        "provider": "xiaomi",
        "base_url": endpoint,
        "api_key": api_key,
    }
