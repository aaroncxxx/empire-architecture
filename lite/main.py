#!/usr/bin/env python3
"""
帝国架构 v1.6 - CLI
Empire Architecture v1.6 - Decentralized P2P + Knowledge Auto-Trigger + 科举制度

用法:
  python3 main.py              # 交互模式
  python3 main.py "指令"        # 单次执行
  python3 main.py --status     # 查看状态
  python3 main.py --knowledge  # 知识层状态
  python3 main.py --keju       # 科举状态
"""
import asyncio
import json
import sys
import os
import signal
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from chancellor import Chancellor


class EmpireCLI:
    """帝国控制台 v1.6"""

    def __init__(self):
        self.chancellor = Chancellor()
        self.running = True

    def print_banner(self):
        print("""
╔══════════════════════════════════════════════════════╗
║       帝国架构 v1.6  Empire Architecture             ║
║──────────────────────────────────────────────────────║
║  皇帝: AARONCXXX    丞相: Mimo                      ║
║  参谋: 3人          执行: 3人                        ║
║  安全: 锦衣卫       总计: 9个节点                     ║
║                                                      ║
║  ⚡ v1.6 新特性:                                     ║
║    🔀 并行分发 + 超时保护                             ║
║    📚 查曹自动触发知识路由                            ║
║    🤝 节点间 P2P 协作                                ║
║    🔄 节点超时 + 失败重试                             ║
║    🎭 柔性角色调度                                    ║
║    📜 科举制度 (九品中正制)                           ║
╚══════════════════════════════════════════════════════╝
        """)

    def print_help(self):
        print("""
命令:
  <指令>             向帝国下达指令
  status             查看帝国状态
  agents             查看所有节点状态
  tokens             查看 token 使用情况
  capabilities       查看节点能力画像
  knowledge          查看知识层状态
  history            查看消息历史
  help               显示帮助
  exit / quit        退出

📜 科举制度:
  keju               科举系统总览
  keju officials     查看所有官员
  keju reserves      查看替补池
  keju training      查看翰林院进修中的候补
  keju exam          举行科举考试（自动考核候补+晋升）
  keju register <名> 注册替补候选人
  keju top           科举排行榜
  keju ranks         官阶分布
  keju positions     官位状态
        """)

    async def execute_command(self, command: str):
        """执行皇帝指令"""
        print(f"\n⚡ 丞相接令，开始编排...")
        print(f"{'─' * 50}")

        try:
            result = await self.chancellor.receive_command(command)

            # 打印结果
            print(f"\n📋 任务 {result['task_id']} 完成 ({result['elapsed_seconds']}s)")
            print(f"{'─' * 50}")

            for agent_id, content in result["results"].items():
                if agent_id == "chancellor_summary":
                    continue
                if agent_id == "p2p_supplement":
                    if isinstance(content, dict) and content:
                        print(f"\n🔗 P2P 节点间协作:")
                        for pair, reply in content.items():
                            display = reply[:300] + "..." if len(reply) > 300 else reply
                            print(f"  {pair}: {display}")
                    continue

                agent = self.chancellor.agents.get(agent_id)
                name = agent.state.name if agent else agent_id

                if isinstance(content, dict):
                    text = content.get("result", "")
                    knowledge_tag = " 📚" if content.get("knowledge_used") else ""
                else:
                    text = str(content)
                    knowledge_tag = ""

                display = text[:500] + "..." if len(text) > 500 else text
                print(f"\n🔸 {name}{knowledge_tag}:")
                print(f"  {display}")

            print(f"\n{'═' * 50}")
            print(f"📊 丞相汇总:")
            summary = result["results"].get("chancellor_summary", "无汇总")
            print(summary)

            audit = result.get("audit", {})
            safe_icon = "✅" if audit.get("safe", True) else "⚠️"
            print(f"\n{safe_icon} 锦衣卫审计: {'通过' if audit.get('safe', True) else '发现问题'}")
            if audit.get("issues"):
                for issue in audit["issues"]:
                    print(f"   - {issue}")

            nodes = result.get("nodes_status", {})
            failed = [aid for aid, s in nodes.items()
                      if isinstance(s, dict) and s.get("tasks_failed", 0) > 0]
            if failed:
                print(f"\n⚠️  节点失败: {', '.join(failed)}")

            print(f"\n⏱  耗时: {result['elapsed_seconds']}s | Token 今日消耗: {result['tokens_used']}")

        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()

    def show_status(self):
        status = self.chancellor.get_status()
        print(f"\n{'═' * 50}")
        print(f"帝国状态 (v{status.get('version', '?')})")
        print(f"{'─' * 50}")
        print(f"节点数: {len(status['agents'])}")
        print(f"消息总数: {status['message_history']}")
        print(f"安全事件: {status['security']['total_violations']}")

        kl = status.get("knowledge_layer", {})
        if kl.get("router_loaded"):
            sources = kl.get("sources", [])
            print(f"知识层: ✅ 已加载 ({len(sources)} 知识源)")
        else:
            print(f"知识层: ❌ 未加载")

        kj = status.get("keju")
        if kj:
            print(f"科举: {kj['officials']} 官员 / {kj['reserves']} 候补 / {kj['in_training']} 进修中")

    def show_agents(self):
        status = self.chancellor.get_status()
        print(f"\n{'═' * 50}")
        print(f"节点状态")
        print(f"{'─' * 50}")
        for aid, info in status["agents"].items():
            icon = {"idle": "🟢", "busy": "🟡", "error": "🔴"}.get(info["status"], "⚪")
            failed = f" 失败:{info.get('tasks_failed', 0)}" if info.get("tasks_failed", 0) > 0 else ""
            print(f"  {icon} {info['name']:8s} [{info['role']:10s}] "
                  f"状态:{info['status']:6s} 完成:{info['tasks_completed']}{failed} "
                  f"运行:{info['uptime']}s")

    def show_tokens(self):
        usage = self.chancellor.tracker.get_usage()
        print(f"\n{'═' * 50}")
        print(f"Token 使用")
        print(f"{'─' * 50}")
        total_input = 0
        total_output = 0
        for agent_id, info in usage.items():
            name = self.chancellor.agents[agent_id].state.name if agent_id in self.chancellor.agents else agent_id
            print(f"  {name:8s} 输入:{info['input']:6d} 输出:{info['output']:6d}")
            total_input += info["input"]
            total_output += info["output"]
        print(f"{'─' * 50}")
        print(f"  总计    输入:{total_input:6d} 输出:{total_output:6d} 合计:{total_input + total_output}")

    def show_capabilities(self):
        """v1.6: 节点能力画像"""
        print(f"\n{'═' * 50}")
        print(f"节点能力画像 (v1.6)")
        print(f"{'─' * 50}")
        for aid, agent in self.chancellor.agents.items():
            s = agent.state
            caps = ", ".join(s.capabilities) if s.capabilities else "—"
            assists = ", ".join(s.assist_roles) if s.assist_roles else "—"
            print(f"\n  🏷️  {s.name} ({aid})")
            print(f"     擅长: {caps}")
            print(f"     可协助: {assists}")
            print(f"     完成:{s.tasks_completed} 失败:{s.tasks_failed}")

    async def show_knowledge(self):
        """v1.6: 知识层状态"""
        print(f"\n{'═' * 50}")
        print(f"知识层状态")
        print(f"{'─' * 50}")

        if not self.chancellor.knowledge_router:
            print("  ❌ 知识层未加载。请确保 knowledge/mount.py 已初始化。")
            return

        sources = self.chancellor.knowledge_router.list_sources()
        print(f"  已注册知识源: {len(sources)}")
        for s in sources:
            print(f"    📚 {s}")

        print(f"\n  正在检查知识源状态...")
        try:
            health = await self.chancellor.knowledge_router.health_all()
            for name, ok in health.items():
                icon = "✅" if ok else "❌"
                print(f"    {icon} {name}")
        except Exception as e:
            print(f"    ⚠️ 健康检查异常: {e}")

    # ═══════════════════ 科举制度命令 ═══════════════════

    def show_keju_overview(self):
        """科举系统总览"""
        kj = self.chancellor.keju
        status = kj.get_full_status()
        print(f"\n{'═' * 50}")
        print(f"📜 科举制度 — 九品中正制")
        print(f"{'─' * 50}")
        print(f"  总候选人数: {status['total_candidates']}")
        print(f"  正式官员:   {status['officials']} / 256")
        print(f"  候补替补:   {status['reserves']} / 1024")
        print(f"  翰林院进修: {status['in_training']}")
        print(f"  已举行考试: {status['exams_conducted']}")

        pos = status.get("positions", {})
        print(f"\n  官位状态:")
        print(f"    总官位: {pos.get('total_positions', 0)}")
        print(f"    已占:   {pos.get('filled', 0)}")
        print(f"    空缺:   {pos.get('vacant', 0)}")

        if status.get("top_officials"):
            print(f"\n  🏆 官员排行榜 TOP {len(status['top_officials'])}:")
            for i, c in enumerate(status["top_officials"], 1):
                rank_name = c.get("rank_name", "未入品")
                print(f"    {i}. {c['name']} [{rank_name}] "
                      f"综合:{c['composite']} 质量:{c['quality']} "
                      f"可靠:{c['reliability']} 任务:{c['tasks']}")

    def show_keju_officials(self):
        """查看所有官员"""
        officials = self.chancellor.keju.get_officials()
        print(f"\n{'═' * 50}")
        print(f"📜 正式官员 ({len(officials)} / 256)")
        print(f"{'─' * 50}")
        if not officials:
            print("  暂无正式官员。科举及第方可入品。")
            return
        # 按品级排序
        officials.sort(key=lambda x: x["rank"])
        for c in officials:
            print(f"  {c['rank_name']:4s} {c['name']:10s} "
                  f"综合:{c['composite']:5.1f} "
                  f"质量:{c['quality']:5.1f} 速度:{c['speed']:5.1f} "
                  f"可靠:{c['reliability']:5.1f} 协作:{c['collab']:5.1f} "
                  f"任务:{c['tasks']} 考试:{c['exams']}")

    def show_keju_reserves(self):
        """查看替补池"""
        reserves = self.chancellor.keju.get_reserves()
        print(f"\n{'═' * 50}")
        print(f"📜 候补替补池 ({len(reserves)} / 1024)")
        print(f"{'─' * 50}")
        if not reserves:
            print("  暂无候补。用 'keju register <名>' 注册。")
            return
        reserves.sort(key=lambda x: x["composite"], reverse=True)
        for i, c in enumerate(reserves[:20], 1):
            status_icon = {"active": "🟢", "training": "📖", "exam": "📝"}.get(c["status"], "⚪")
            print(f"  {i:3d}. {status_icon} {c['name']:10s} "
                  f"综合:{c['composite']:5.1f} "
                  f"任务:{c['tasks']} 失败:{c['failed']} "
                  f"考试:{c['exams']} 进修:{c['training']}")
        if len(reserves) > 20:
            print(f"  ... 还有 {len(reserves) - 20} 人")

    def show_keju_training(self):
        """查看翰林院进修"""
        training = self.chancellor.keju.get_training()
        print(f"\n{'═' * 50}")
        print(f"📜 翰林院进修 ({len(training)} 人)")
        print(f"{'─' * 50}")
        if not training:
            print("  翰林院空空如也。")
            return
        for c in training:
            print(f"  📖 {c['name']:10s} "
                  f"综合:{c['composite']:5.1f} "
                  f"质量:{c['quality']:5.1f} 可靠:{c['reliability']:5.1f} "
                  f"进修轮次:{c['training']}")

    async def run_keju_exam(self):
        """举行科举考试"""
        print(f"\n📜 丞相主持科举考试...")
        print(f"{'─' * 50}")

        # 自动考核候补 + 晋升
        await self.chancellor.run_examination_cycle()

        # 显示结果
        kj = self.chancellor.keju
        recent_exams = kj.exam_history[-10:]
        if recent_exams:
            print(f"\n  考试结果:")
            for e in recent_exams:
                icon = "✅" if e.passed else "❌"
                c = kj.candidates.get(e.candidate_id)
                name = c.name if c else e.candidate_id
                print(f"    {icon} {name} → {e.feedback} ({e.total:.1f}分)")
        else:
            print("  暂无需要考核的候补或官员。")

        print(f"\n  科举统计: {kj.get_full_status()['officials']} 官员 / "
              f"{kj.get_full_status()['reserves']} 候补 / "
              f"{kj.get_full_status()['in_training']} 进修中")

    def register_keju_candidate(self, name: str):
        """注册替补候选人"""
        try:
            c = self.chancellor.keju.register_candidate(name)
            print(f"\n✅ 候补注册成功!")
            print(f"  姓名: {c.name}")
            print(f"  ID:   {c.candidate_id}")
            print(f"  品级: 未入品（候补）")
            print(f"  通过科举考试方可入品为官。")
        except ValueError as e:
            print(f"\n❌ 注册失败: {e}")

    def show_keju_top(self):
        """科举排行榜"""
        kj = self.chancellor.keju
        all_candidates = sorted(
            kj.candidates.values(),
            key=lambda x: x.composite_score,
            reverse=True,
        )[:20]

        print(f"\n{'═' * 50}")
        print(f"🏆 科举排行榜 TOP 20")
        print(f"{'─' * 50}")
        for i, c in enumerate(all_candidates, 1):
            rank_name = c.to_dict().get("rank_name", "未入品")
            tier = c.to_dict().get("tier", "候补")
            status_icon = {"active": "🟢", "training": "📖", "exam": "📝"}.get(c.status, "⚪")
            print(f"  {i:2d}. {status_icon} [{rank_name:4s}] {c.name:10s} "
                  f"综合:{c.composite_score:5.1f} "
                  f"质:{c.quality_score:5.1f} 速:{c.speed_score:5.1f} "
                  f"信:{c.reliability_score:5.1f} 协:{c.collab_score:5.1f} "
                  f"任务:{c.tasks_completed}")

    def show_keju_ranks(self):
        """官阶分布"""
        dist = self.chancellor.keju.get_rank_distribution()
        print(f"\n{'═' * 50}")
        print(f"📜 九品中正制 — 官阶分布")
        print(f"{'─' * 50}")
        for rank_name, count in dist.items():
            if count > 0:
                bar = "█" * min(count, 40)
                print(f"  {rank_name:4s} {count:3d} {bar}")
        total_officials = sum(v for k, v in dist.items() if k != "未入品")
        print(f"{'─' * 50}")
        print(f"  官员: {total_officials}/256 | 候补: {dist.get('未入品', 0)}/1024")

    def show_keju_positions(self):
        """官位状态"""
        ps = self.chancellor.keju.get_position_status()
        print(f"\n{'═' * 50}")
        print(f"📜 官位状态")
        print(f"{'─' * 50}")
        print(f"  总官位: {ps['total_positions']} | 已占: {ps['filled']} | 空缺: {ps['vacant']}")
        print(f"\n  {'品级':4s} {'总数':4s} {'已占':4s} {'空缺':4s}")
        print(f"  {'─' * 20}")
        for rank_name, info in ps.get("by_rank", {}).items():
            filled = info["filled"]
            total = info["total"]
            vacant = total - filled
            bar = "█" * filled + "░" * vacant
            print(f"  {rank_name:4s} {total:4d} {filled:4d} {vacant:4d} {bar}")

    def show_history(self):
        history = self.chancellor.bus.get_history(20)
        print(f"\n{'═' * 50}")
        print(f"最近消息 (最新20条)")
        print(f"{'─' * 50}")
        for msg in history:
            ts = time.strftime("%H:%M:%S", time.localtime(msg.timestamp))
            print(f"  [{ts}] {msg.sender} → {msg.receiver} ({msg.msg_type.value}): {msg.content[:80]}")

    async def handle_keju_command(self, args: list):
        """处理科举子命令"""
        if not args:
            self.show_keju_overview()
            return

        sub = args[0].lower()
        if sub == "officials":
            self.show_keju_officials()
        elif sub == "reserves":
            self.show_keju_reserves()
        elif sub == "training":
            self.show_keju_training()
        elif sub == "exam":
            await self.run_keju_exam()
        elif sub == "register":
            name = args[1] if len(args) > 1 else f"候补{len(self.chancellor.keju.candidates)+1}"
            self.register_keju_candidate(name)
        elif sub == "top":
            self.show_keju_top()
        elif sub == "ranks":
            self.show_keju_ranks()
        elif sub == "positions":
            self.show_keju_positions()
        else:
            print(f"  未知科举命令: {sub}")
            print("  可用: officials / reserves / training / exam / register / top / ranks / positions")

    async def interactive(self):
        """交互模式"""
        self.print_banner()
        self.print_help()

        while self.running:
            try:
                cmd = input("\n👑 皇帝> ").strip()
                if not cmd:
                    continue

                parts = cmd.split()
                base = parts[0].lower()

                if base in ("exit", "quit", "q"):
                    print("帝国关闭。皇帝万岁。")
                    break
                elif base == "help":
                    self.print_help()
                elif base == "status":
                    self.show_status()
                elif base == "agents":
                    self.show_agents()
                elif base == "tokens":
                    self.show_tokens()
                elif base == "capabilities":
                    self.show_capabilities()
                elif base == "knowledge":
                    await self.show_knowledge()
                elif base == "history":
                    self.show_history()
                elif base == "keju":
                    await self.handle_keju_command(parts[1:])
                else:
                    await self.execute_command(cmd)

            except KeyboardInterrupt:
                print("\n帝国关闭。")
                break
            except EOFError:
                break


async def main():
    cli = EmpireCLI()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--status":
            cli.show_status()
        elif arg == "--agents":
            cli.show_agents()
        elif arg == "--tokens":
            cli.show_tokens()
        elif arg == "--capabilities":
            cli.show_capabilities()
        elif arg == "--knowledge":
            await cli.show_knowledge()
        elif arg == "--keju":
            if len(sys.argv) > 2:
                await cli.handle_keju_command(sys.argv[2:])
            else:
                cli.show_keju_overview()
        else:
            command = " ".join(sys.argv[1:])
            await cli.execute_command(command)
    else:
        await cli.interactive()


if __name__ == "__main__":
    asyncio.run(main())
