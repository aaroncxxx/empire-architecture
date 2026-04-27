"""帝国架构 - Token 追踪 v2.0"""
import sqlite3
import time
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tokens.db")


class TokenTracker:
    """Token 消耗追踪"""

    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
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
        """)
        self.conn.commit()

    def log_usage(self, agent_id: str, input_tokens: int, output_tokens: int,
                  model: str = "", task_id: str = ""):
        now = time.time()
        self.conn.execute(
            "INSERT INTO token_usage (agent_id, task_id, input_tokens, output_tokens, model, timestamp) VALUES (?,?,?,?,?,?)",
            (agent_id, task_id, input_tokens, output_tokens, model, now),
        )
        # 确保 budget 行存在，然后累加
        self.conn.execute(
            "INSERT OR IGNORE INTO token_budget (agent_id, daily_limit, used_today, last_reset) VALUES (?, 100000, 0, date('now'))",
            (agent_id,),
        )
        # 自动跨日重置
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
        """获取今日总 token 消耗（从实际 usage 表按日期统计）"""
        today_start = self._today_timestamp()
        row = self.conn.execute(
            "SELECT COALESCE(SUM(input_tokens + output_tokens), 0) FROM token_usage WHERE timestamp >= ?",
            (today_start,),
        ).fetchone()
        return row[0] if row else 0

    def _today_timestamp(self) -> float:
        """获取今天 00:00:00 的 Unix 时间戳"""
        import datetime
        now = datetime.datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.timestamp()

    def reset_daily(self):
        self.conn.execute("UPDATE token_budget SET used_today = 0, last_reset = date('now')")
        self.conn.commit()

    def set_budget(self, agent_id: str, daily_limit: int):
        self.conn.execute(
            "INSERT OR REPLACE INTO token_budget (agent_id, daily_limit, used_today, last_reset) VALUES (?, ?, 0, date('now'))",
            (agent_id, daily_limit),
        )
        self.conn.commit()

    def check_budget(self, agent_id: str) -> bool:
        """检查是否还有 token 额度"""
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
        # 跨日重置
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
