"""帝国架构 v2.9 - 日志系统"""
import logging
import os
import time
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ─── 格式 ───
_FMT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
_DATE = "%Y-%m-%d %H:%M:%S"

def get_logger(name: str, level=logging.INFO) -> logging.Logger:
    """获取带文件轮转的 logger"""
    logger = logging.getLogger(f"empire.{name}")
    if logger.handlers:
        return logger
    logger.setLevel(level)

    # 控制台
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter(_FMT, _DATE))
    logger.addHandler(ch)

    # 文件（10MB 轮转，保留 5 个）
    fh = RotatingFileHandler(
        os.path.join(LOG_DIR, f"{name}.log"),
        maxBytes=10*1024*1024, backupCount=5, encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(_FMT, _DATE))
    logger.addHandler(fh)

    return logger

# 全局 logger
log = get_logger("core")
