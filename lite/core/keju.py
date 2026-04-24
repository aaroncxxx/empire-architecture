"""
帝国架构 v1.6 — 科举制度 / Imperial Examination System

灵感来源：
- 科举制：通过考试选拔人才
- 九品中正制：九级官阶体系
- 翰林院：进修学习、等待晋升

核心机制：
- 替补池：最多 1024 个外部 Agent（贡献算力）
- 官员名额：最多 256 个正式职位
- 九品官阶：正一品 → 正九品 + 未入品
- 科举考试：定期考核，择优晋升
- 翰林院进修：待考察 Agent 学习等待
"""
import asyncio
import json
import time
import uuid
import os
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


# ═══════════════════════ 九品官阶 ═══════════════════════

class Rank(IntEnum):
    """九品中正制 — 官阶体系"""
    UNRANKED = 0    # 未入品（替补/候补）
    NINTH = 9       # 正九品
    EIGHTH = 8      # 正八品
    SEVENTH = 7     # 正七品
    SIXTH = 6       # 正六品
    FIFTH = 5       # 正五品
    FOURTH = 4      # 正四品
    THIRD = 3       # 正三品
    SECOND = 2      # 正二品
    FIRST = 1       # 正一品

    @property
    def cn_name(self) -> str:
        names = {
            0: "未入品",
            9: "正九品", 8: "正八品", 7: "正七品",
            6: "正六品", 5: "正五品", 4: "正四品",
            3: "正三品", 2: "正二品", 1: "正一品",
        }
        return names.get(self.value, "未知")

    @property
    def tier(self) -> str:
        """品级分层"""
        if self.value >= 7:
            return "基层"   # 7-9品：基层官员
        elif self.value >= 4:
            return "中层"   # 4-6品：中层官员
        elif self.value >= 1:
            return "高层"   # 1-3品：高层官员
        return "候补"

    @property
    def position_type(self) -> str:
        """对应官职类型"""
        mapping = {
            9: "书吏", 8: "主簿", 7: "县丞",
            6: "侍郎", 5: "郎中", 4: "学士",
            3: "大学士", 2: "尚书", 1: "太师/太傅",
        }
        return mapping.get(self.value, "候补生")


# ═══════════════════════ 候选人 ═══════════════════════

@dataclass
class Candidate:
    """替补候选人 / Reserve Candidate"""
    candidate_id: str
    name: str
    rank: int = Rank.UNRANKED       # 当前品级
    status: str = "active"           # active / training / exam / promoted / expelled

    # 算力贡献
    compute_contributed: float = 0.0  # 累计贡献算力（秒）
    tasks_completed: int = 0
    tasks_failed: int = 0

    # 考核成绩
    quality_score: float = 0.0       # 质量分 (0-100)
    speed_score: float = 0.0         # 速度分 (0-100)
    reliability_score: float = 0.0   # 可靠性分 (0-100)
    collab_score: float = 0.0        # 协作分 (0-100)
    exam_score: float = 0.0          # 科举总分 (0-100)

    # 记录
    joined_at: float = field(default_factory=time.time)
    last_exam_at: float = 0.0
    promoted_at: float = 0.0
    exam_attempts: int = 0
    training_rounds: int = 0

    # 能力标签（继承 Agent 的 capabilities）
    capabilities: list = field(default_factory=list)

    @property
    def composite_score(self) -> float:
        """综合评分 = 加权平均"""
        return (
            self.quality_score * 0.40 +
            self.speed_score * 0.20 +
            self.reliability_score * 0.25 +
            self.collab_score * 0.15
        )

    @property
    def is_official(self) -> bool:
        return self.rank > Rank.UNRANKED and self.status == "active"

    def to_dict(self) -> dict:
        return {
            "id": self.candidate_id,
            "name": self.name,
            "rank": self.rank,
            "rank_name": Rank(self.rank).cn_name if self.rank > 0 else "未入品",
            "tier": Rank(self.rank).tier if self.rank > 0 else "候补",
            "status": self.status,
            "composite": round(self.composite_score, 1),
            "quality": round(self.quality_score, 1),
            "speed": round(self.speed_score, 1),
            "reliability": round(self.reliability_score, 1),
            "collab": round(self.collab_score, 1),
            "tasks": self.tasks_completed,
            "failed": self.tasks_failed,
            "compute": round(self.compute_contributed, 1),
            "exams": self.exam_attempts,
            "training": self.training_rounds,
        }


# ═══════════════════════ 官位 ═══════════════════════

@dataclass
class OfficialPosition:
    """官位 / Official Position"""
    position_id: str
    rank: int                       # 品级
    title: str                      # 官职名
    occupant_id: Optional[str] = None  # 占位者
    department: str = ""            # 所属部门
    created_at: float = field(default_factory=time.time)

    @property
    def is_vacant(self) -> bool:
        return self.occupant_id is None

    def to_dict(self) -> dict:
        return {
            "id": self.position_id,
            "rank": self.rank,
            "rank_name": Rank(self.rank).cn_name,
            "title": self.title,
            "occupant": self.occupant_id,
            "vacant": self.is_vacant,
            "department": self.department,
        }


# ═══════════════════════ 科举考试 ═══════════════════════

class ExaminationType:
    """考试类型"""
    QUALIFYING = "qualifying"   # 资格考试（替补 → 入品）
    PROMOTION = "promotion"     # 晋升考试（升品）
    REVIEW = "review"           # 复查考试（降品风险时）


@dataclass
class ExamResult:
    """考试结果"""
    exam_id: str
    candidate_id: str
    exam_type: str
    target_rank: int

    quality: float = 0.0
    speed: float = 0.0
    reliability: float = 0.0
    collab: float = 0.0
    total: float = 0.0

    passed: bool = False
    feedback: str = ""
    conducted_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "exam_id": self.exam_id,
            "candidate": self.candidate_id,
            "type": self.exam_type,
            "target_rank": self.target_rank,
            "total": round(self.total, 1),
            "passed": self.passed,
            "feedback": self.feedback,
        }


# ═══════════════════════ 科举院 ═══════════════════════

MAX_RESERVES = 1024        # 最大替补数
MAX_OFFICIALS = 256        # 最大官员数
EXAM_PASS_SCORE = 60.0     # 及格线
TRAINING_DURATION = 3      # 翰林院进修轮数
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "keju.db")


class ImperialExamination:
    """科举院 — 选拔、考核、晋升总管"""

    def __init__(self, db_path: str = DB_PATH):
        self.candidates: dict[str, Candidate] = {}
        self.positions: dict[str, OfficialPosition] = {}
        self.exam_history: list[ExamResult] = []

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db_path = db_path
        self._init_positions()
        self._init_db()

    def _init_db(self):
        """持久化数据库"""
        import sqlite3
        self.conn = sqlite3.connect(self._db_path)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                name TEXT,
                rank INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                compute_contributed REAL DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0,
                speed_score REAL DEFAULT 0,
                reliability_score REAL DEFAULT 0,
                collab_score REAL DEFAULT 0,
                exam_score REAL DEFAULT 0,
                joined_at REAL,
                last_exam_at REAL DEFAULT 0,
                promoted_at REAL DEFAULT 0,
                exam_attempts INTEGER DEFAULT 0,
                training_rounds INTEGER DEFAULT 0,
                capabilities TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS exam_history (
                exam_id TEXT PRIMARY KEY,
                candidate_id TEXT,
                exam_type TEXT,
                target_rank INTEGER,
                quality REAL, speed REAL, reliability REAL, collab REAL,
                total REAL, passed INTEGER, feedback TEXT,
                conducted_at REAL
            );
            CREATE TABLE IF NOT EXISTS positions (
                position_id TEXT PRIMARY KEY,
                rank INTEGER,
                title TEXT,
                occupant_id TEXT,
                department TEXT,
                created_at REAL
            );
        """)
        self.conn.commit()

    def _init_positions(self):
        """初始化官位体系 — 按九品中正制分配"""
        position_templates = [
            # (品级, 官职名, 部门, 数量)
            (1, "太师", "中枢", 2),
            (1, "太傅", "中枢", 2),
            (2, "尚书", "六部", 6),
            (2, "大将军", "军机", 2),
            (3, "大学士", "翰林院", 4),
            (3, "侍中", "门下", 4),
            (4, "学士", "翰林院", 8),
            (4, "侍郎", "六部", 8),
            (5, "郎中", "六部", 16),
            (5, "御史", "都察院", 8),
            (6, "员外郎", "六部", 16),
            (6, "主事", "六部", 16),
            (7, "县丞", "地方", 32),
            (7, "教谕", "地方", 16),
            (8, "主簿", "地方", 32),
            (8, "典史", "地方", 16),
            (9, "书吏", "各部", 32),
            (9, "驿丞", "驿传", 16),
        ]

        pid = 0
        for rank, title, dept, count in position_templates:
            for i in range(count):
                pid += 1
                pos_id = f"pos_{pid:04d}"
                self.positions[pos_id] = OfficialPosition(
                    position_id=pos_id,
                    rank=rank,
                    title=f"{title}" + (f"#{i+1}" if count > 1 else ""),
                    department=dept,
                )

    # ─────────── 注册 / 登记 ───────────

    def register_candidate(self, name: str,
                           capabilities: list = None) -> Candidate:
        """注册替补候选人"""
        if len(self.candidates) >= MAX_RESERVES + MAX_OFFICIALS:
            raise ValueError(f"替补池已满（上限 {MAX_RESERVES} 人）")

        cid = f"candidate_{uuid.uuid4().hex[:8]}"
        candidate = Candidate(
            candidate_id=cid,
            name=name,
            capabilities=capabilities or [],
        )
        self.candidates[cid] = candidate
        self._save_candidate(candidate)
        return candidate

    # ─────────── 考核评分 ───────────

    def evaluate_task(self, candidate_id: str,
                      task_result: str,
                      task_elapsed: float,
                      success: bool,
                      collaboration_bonus: float = 0.0):
        """每次任务执行后的评分更新"""
        c = self.candidates.get(candidate_id)
        if not c:
            return

        if success:
            c.tasks_completed += 1
            # 质量分：结果长度和结构化程度的简单启发式
            quality = min(100, len(task_result) / 10 + 20)
            if "[ERROR]" in task_result:
                quality *= 0.3
            c.quality_score = c.quality_score * 0.7 + quality * 0.3

            # 速度分：越快越高（基准 120s）
            speed = max(0, 100 - task_elapsed * 0.5)
            c.speed_score = c.speed_score * 0.7 + speed * 0.3

            # 可靠性分
            total = c.tasks_completed + c.tasks_failed
            c.reliability_score = (c.tasks_completed / total) * 100 if total > 0 else 50
        else:
            c.tasks_failed += 1
            total = c.tasks_completed + c.tasks_failed
            c.reliability_score = (c.tasks_completed / total) * 100 if total > 0 else 50

        # 协作分
        c.collab_score = min(100, c.collab_score + collaboration_bonus * 5)

        # 算力贡献
        c.compute_contributed += task_elapsed
        self._save_candidate(c)

    # ─────────── 科举考试 ───────────

    async def conduct_exam(self, candidate_id: str,
                           exam_type: str = ExaminationType.QUALIFYING,
                           chancellor_agent=None) -> ExamResult:
        """举行科举考试"""
        c = self.candidates.get(candidate_id)
        if not c:
            raise ValueError(f"候选人不存在: {candidate_id}")

        c.status = "exam"
        c.exam_attempts += 1
        c.last_exam_at = time.time()

        exam_id = f"exam_{uuid.uuid4().hex[:8]}"

        # 确定目标品级
        if exam_type == ExaminationType.QUALIFYING:
            target_rank = Rank.NINTH  # 资格考入九品
        elif exam_type == ExaminationType.PROMOTION:
            target_rank = min(c.rank + 1, Rank.FIRST)  # 升一品
        else:
            target_rank = c.rank  # 复查当前品级

        # 考试评分 = 综合历史表现 + 加成
        exam = ExamResult(
            exam_id=exam_id,
            candidate_id=candidate_id,
            exam_type=exam_type,
            target_rank=target_rank,
            quality=c.quality_score,
            speed=c.speed_score,
            reliability=c.reliability_score,
            collab=c.collab_score,
        )

        # 计算总分
        exam.total = (
            exam.quality * 0.35 +
            exam.speed * 0.20 +
            exam.reliability * 0.30 +
            exam.collab * 0.15
        )

        # 如果有丞相 Agent，可以做 AI 评审
        if chancellor_agent and c.tasks_completed >= 3:
            ai_score = await self._ai_review(chancellor_agent, c)
            exam.total = exam.total * 0.6 + ai_score * 0.4

        # 判定
        exam.passed = exam.total >= EXAM_PASS_SCORE
        if exam.passed:
            if exam_type == ExaminationType.QUALIFYING and c.rank == Rank.UNRANKED:
                c.rank = Rank.NINTH
                c.status = "active"
                exam.feedback = f"🎉 恭喜！科举及第，授{Rank.NINTH.cn_name}{Rank.NINTH.position_type}"
            elif exam_type == ExaminationType.PROMOTION:
                old_rank = c.rank
                c.rank = target_rank
                c.status = "active"
                c.promoted_at = time.time()
                exam.feedback = f"⬆️ 晋升！从{Rank(old_rank).cn_name}升至{Rank(target_rank).cn_name}"
            else:
                c.status = "active"
                exam.feedback = "✅ 复查通过，保留现职"
        else:
            if exam_type == ExaminationType.REVIEW:
                c.rank = max(Rank.UNRANKED, c.rank - 1)
                exam.feedback = f"⬇️ 复查未通过，降至{Rank(c.rank).cn_name}"
            elif c.rank == Rank.UNRANKED:
                c.status = "training"
                exam.feedback = f"📚 科举未第（{exam.total:.1f}分），进入翰林院进修"
            else:
                exam.feedback = f"📝 晋升考试未通过（{exam.total:.1f}分），继续努力"
            c.status = "active" if c.rank > Rank.UNRANKED else "training"

        c.exam_score = exam.total
        self.exam_history.append(exam)
        self._save_candidate(c)
        self._save_exam(exam)
        return exam

    async def _ai_review(self, chancellor_agent, candidate: Candidate) -> float:
        """丞相 AI 评审"""
        try:
            prompt = f"""作为丞相，请评审以下候补官员的表现，给出 0-100 分：

候选人：{candidate.name}
品级：{Rank(candidate.rank).cn_name}
完成任务：{candidate.tasks_completed}
失败次数：{candidate.tasks_failed}
质量分：{candidate.quality_score:.1f}
速度分：{candidate.speed_score:.1f}
可靠性：{candidate.reliability_score:.1f}
协作分：{candidate.collab_score:.1f}

请只返回一个 0-100 的数字评分。"""

            result = await chancellor_agent.call_llm(prompt)
            # 提取数字
            import re
            numbers = re.findall(r'\d+\.?\d*', result)
            if numbers:
                score = float(numbers[0])
                return min(100, max(0, score))
        except Exception:
            pass
        return candidate.composite_score

    # ─────────── 翰林院进修 ───────────

    def enter_training(self, candidate_id: str) -> bool:
        """进入翰林院进修"""
        c = self.candidates.get(candidate_id)
        if not c:
            return False
        c.status = "training"
        c.training_rounds += 1
        self._save_candidate(c)
        return True

    def complete_training(self, candidate_id: str) -> bool:
        """完成翰林院进修"""
        c = self.candidates.get(candidate_id)
        if not c:
            return False
        if c.status == "training":
            c.status = "active"
            # 进修加分
            c.quality_score = min(100, c.quality_score + 5)
            c.reliability_score = min(100, c.reliability_score + 3)
            self._save_candidate(c)
            return True
        return False

    async def run_training_cycle(self, chancellor_agent=None):
        """翰林院进修周期 — 所有进修中的候补学习"""
        training_candidates = [
            c for c in self.candidates.values()
            if c.status == "training"
        ]

        for c in training_candidates:
            # 模拟学习：用过去优秀案例做训练
            c.quality_score = min(100, c.quality_score + 3)
            c.speed_score = min(100, c.speed_score + 2)
            c.reliability_score = min(100, c.reliability_score + 2)
            c.collab_score = min(100, c.collab_score + 1)
            c.training_rounds += 1

            # 进修达标 → 自动参加资格考试
            if c.composite_score >= EXAM_PASS_SCORE and c.rank == Rank.UNRANKED:
                c.status = "active"
                await self.conduct_exam(c.candidate_id,
                                        ExaminationType.QUALIFYING,
                                        chancellor_agent)

            self._save_candidate(c)

    # ─────────── 晋升调度 ───────────

    async def run_promotion_cycle(self, chancellor_agent=None):
        """晋升周期 — 符合条件的官员参加晋升考试"""
        for c in self.candidates.values():
            if c.status != "active" or c.rank == Rank.UNRANKED:
                continue
            if c.rank == Rank.FIRST:
                continue  # 已经最高

            # 晋升条件：完成足够任务 + 距上次考试足够久
            min_tasks = (Rank.FIRST - c.rank + 1) * 5  # 品级越高需要越多任务
            time_since_exam = time.time() - c.last_exam_at
            min_interval = 3600  # 1 小时间隔

            if (c.tasks_completed >= min_tasks and
                    time_since_exam >= min_interval and
                    c.composite_score >= 70):
                await self.conduct_exam(c.candidate_id,
                                        ExaminationType.PROMOTION,
                                        chancellor_agent)

    # ─────────── 官位管理 ───────────

    def assign_position(self, candidate_id: str) -> Optional[str]:
        """为候选人分配官位"""
        c = self.candidates.get(candidate_id)
        if not c or c.rank == Rank.UNRANKED:
            return None

        # 找同品级的空缺
        for pos in self.positions.values():
            if pos.rank == c.rank and pos.is_vacant:
                pos.occupant_id = candidate_id
                self._save_position(pos)
                return pos.position_id

        return None

    def vacate_position(self, candidate_id: str):
        """释放官位"""
        for pos in self.positions.values():
            if pos.occupant_id == candidate_id:
                pos.occupant_id = None
                self._save_position(pos)

    # ─────────── 查询 ───────────

    def get_officials(self) -> list[dict]:
        """获取所有正式官员"""
        return [
            c.to_dict() for c in self.candidates.values()
            if c.is_official
        ]

    def get_reserves(self) -> list[dict]:
        """获取所有候补"""
        return [
            c.to_dict() for c in self.candidates.values()
            if c.rank == Rank.UNRANKED
        ]

    def get_training(self) -> list[dict]:
        """获取翰林院进修中的候补"""
        return [
            c.to_dict() for c in self.candidates.values()
            if c.status == "training"
        ]

    def get_candidate(self, candidate_id: str) -> Optional[dict]:
        c = self.candidates.get(candidate_id)
        return c.to_dict() if c else None

    def get_rank_distribution(self) -> dict:
        """官阶分布"""
        dist = {r.cn_name: 0 for r in Rank}
        for c in self.candidates.values():
            rank = Rank(c.rank) if c.rank in [r.value for r in Rank] else Rank.UNRANKED
            dist[rank.cn_name] += 1
        return dist

    def get_position_status(self) -> dict:
        """官位状态"""
        total = len(self.positions)
        filled = sum(1 for p in self.positions.values() if not p.is_vacant)
        by_rank = {}
        for pos in self.positions.values():
            key = Rank(pos.rank).cn_name
            if key not in by_rank:
                by_rank[key] = {"total": 0, "filled": 0}
            by_rank[key]["total"] += 1
            if not pos.is_vacant:
                by_rank[key]["filled"] += 1
        return {
            "total_positions": total,
            "filled": filled,
            "vacant": total - filled,
            "max_officials": MAX_OFFICIALS,
            "max_reserves": MAX_RESERVES,
            "by_rank": by_rank,
        }

    def get_full_status(self) -> dict:
        """完整科举系统状态"""
        officials = [c for c in self.candidates.values() if c.is_official]
        reserves = [c for c in self.candidates.values() if c.rank == Rank.UNRANKED]
        training = [c for c in self.candidates.values() if c.status == "training"]

        # 顶级官员 TOP 5
        top5 = sorted(officials, key=lambda x: x.composite_score, reverse=True)[:5]

        return {
            "total_candidates": len(self.candidates),
            "officials": len(officials),
            "reserves": len(reserves),
            "in_training": len(training),
            "positions": self.get_position_status(),
            "rank_distribution": self.get_rank_distribution(),
            "top_officials": [c.to_dict() for c in top5],
            "exams_conducted": len(self.exam_history),
        }

    # ─────────── 持久化 ───────────

    def _save_candidate(self, c: Candidate):
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO candidates VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                c.candidate_id, c.name, c.rank, c.status,
                c.compute_contributed, c.tasks_completed, c.tasks_failed,
                c.quality_score, c.speed_score, c.reliability_score,
                c.collab_score, c.exam_score, c.joined_at,
                c.last_exam_at, c.promoted_at, c.exam_attempts,
                c.training_rounds, json.dumps(c.capabilities),
            ))
            self.conn.commit()
        except Exception:
            pass

    def _save_exam(self, e: ExamResult):
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO exam_history VALUES
                (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                e.exam_id, e.candidate_id, e.exam_type, e.target_rank,
                e.quality, e.speed, e.reliability, e.collab,
                e.total, 1 if e.passed else 0, e.feedback,
            ))
            self.conn.commit()
        except Exception:
            pass

    def _save_position(self, pos: OfficialPosition):
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO positions VALUES (?,?,?,?,?,?)
            """, (
                pos.position_id, pos.rank, pos.title,
                pos.occupant_id, pos.department, pos.created_at,
            ))
            self.conn.commit()
        except Exception:
            pass
