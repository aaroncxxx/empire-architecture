"""帝国架构 v2.9 - Token 追踪（增强版）"""
import sqlite3
import time
import os
import threading
from datetime import date
from .logger import get_logger

log = get_logger("tokens")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tokens.db")


class TokenTracker:
    """Token 消耗追踪 v2.9 - WAL 模式 + 线程安全 + 按模型统计"""

    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                task_id TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                model TEXT,
                timestamp REAL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS token_budget (
                agent_id TEXT PRIMARY KEY,
                daily_limit INTEGER DEFAULT 100000,
                used_today INTEGER DEFAULT 0,
                last_reset TEXT DEFAULT (date('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_usage_ts ON token_usage(timestamp);
            CREATE INDEX IF NOT EXISTS idx_usage_agent ON token_usage(agent_id);
        """)
        self.conn.commit()

    def log_usage(self, agent_id: str, input_tokens: int, output_tokens: int,
                  model: str = "", task_id: str = ""):
        now = time.time()
        with self._lock:
            self.conn.execute(
                "INSERT INTO token_usage (agent_id, task_id, input_tokens, output_tokens, model, timestamp) VALUES (?,?,?,?,?,?)",
                (agent_id, task_id, input_tokens, output_tokens, model, now),
            )
            self.conn.execute(
                "INSERT OR IGNORE INTO token_budget (agent_id, daily_limit, used_today, last_reset) VALUES (?, 100000, 0, date('now'))",
                (agent_id,),
            )
            self.conn.execute(
                """UPDATE token_budget
                   SET used_today = CASE
                     WHEN last_reset < date('now') THEN ?
                     ELSE used_today + ?
                   END,
                   last_reset = date('now')
                   WHERE agent_id = ?""",
                (input_tokens + output_tokens, input_tokens + output_tokens, agent_id),
            )
            self.conn.commit()

    def get_usage(self, agent_id: str = None) -> dict:
        with self._lock:
            if agent_id:
                row = self.conn.execute(
                    "SELECT used_today, daily_limit FROM token_budget WHERE agent_id = ?",
                    (agent_id,),
                ).fetchone()
                return {"used": row[0] if row else 0, "limit": row[1] if row else 100000}
            rows = self.conn.execute(
                "SELECT agent_id, SUM(input_tokens), SUM(output_tokens) FROM token_usage GROUP BY agent_id"
            ).fetchall()
            return {r[0]: {"input": r[1] or 0, "output": r[2] or 0} for r in rows}

    def get_total_today(self) -> int:
        today_start = self._today_timestamp()
        with self._lock:
            row = self.conn.execute(
                "SELECT COALESCE(SUM(input_tokens + output_tokens), 0) FROM token_usage WHERE timestamp >= ?",
                (today_start,),
            ).fetchone()
            return row[0] if row else 0

    def get_model_stats(self) -> dict:
        """v2.9: 按模型统计消耗"""
        with self._lock:
            rows = self.conn.execute(
                "SELECT model, SUM(input_tokens), SUM(output_tokens), COUNT(*) FROM token_usage WHERE model GROUP BY model"
            ).fetchall()
            return {r[0]: {"input": r[1], "output": r[2], "calls": r[3]} for r in rows}

    def _today_timestamp(self) -> float:
        import datetime
        now = datetime.datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.timestamp()

    def check_budget(self, agent_id: str) -> bool:
        with self._lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO token_budget (agent_id, daily_limit, used_today, last_reset) VALUES (?, 100000, 0, date('now'))",
                (agent_id,),
            )
            self.conn.commit()
            row = self.conn.execute(
                "SELECT used_today, daily_limit FROM token_budget WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
            if not row:
                return True
            today = date.today().isoformat()
            last = self.conn.execute(
                "SELECT last_reset FROM token_budget WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            if last and last[0] < today:
                self.conn.execute(
                    "UPDATE token_budget SET used_today = 0, last_reset = date('now') WHERE agent_id = ?",
                    (agent_id,),
                )
                self.conn.commit()
                return True
            return row[0] < row[1]

    def set_budget(self, agent_id: str, daily_limit: int):
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO token_budget (agent_id, daily_limit, used_today, last_reset) VALUES (?, ?, 0, date('now'))",
                (agent_id, daily_limit),
            )
            self.conn.commit()
