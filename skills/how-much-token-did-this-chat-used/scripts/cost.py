#!/usr/bin/env python3
"""
MiMo Token Cost Calculator v2.1
Usage:
  python3 cost.py --input <in> --output <out> --total <total> --used <used> --credit <credit> --avg <avg> [--model <model>]
  python3 cost.py --list-models
  python3 cost.py --help

Changelog v2.1:
  - 新增近 7 天消耗趋势（文本柱状图）
  - 新增费用告警阈值 --warn（80%/95%）
  - 新增按会话分列 Top 烧钱会话
  - 剩余天数改为加权平均（近3天60% + 近7天30% + 近30天10%）
  - --json 增强：trend / top_sessions / alerts 字段
  - 输出格式优化
"""

import sys
import argparse
import json
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

MODEL_RATES = {
    "mimo-v2-pro":    {"unit": "CNY", "input": 0.002, "output": 0.004},
    "mimo-v2.5-pro":  {"unit": "CNY", "input": 0.002, "output": 0.004},
    "mimo-v2.5":      {"unit": "CNY", "input": 0.002, "output": 0.004},
    "mimo-v2":        {"unit": "CNY", "input": 0.002, "output": 0.004},
}

DEFAULT_RATE = {"unit": "CNY", "input": 0.002, "output": 0.004}


def detect_rate(model: str) -> dict:
    model_lower = model.lower()
    for key, rate in MODEL_RATES.items():
        if key == model_lower:
            return rate
    for key, rate in MODEL_RATES.items():
        if key in model_lower:
            return rate
    return DEFAULT_RATE


def calc_session_cost(input_tokens: int, output_tokens: int, rate: dict) -> float:
    return round((input_tokens * rate["input"] + output_tokens * rate["output"]) / 1000, 4)


def calc_total_cost(total_tokens: int, input_tokens: int, output_tokens: int, rate: dict) -> float:
    io_total = input_tokens + output_tokens
    input_ratio = input_tokens / io_total if io_total > 0 else 0.7
    return round(
        (total_tokens * input_ratio * rate["input"] +
         total_tokens * (1 - input_ratio) * rate["output"]) / 1000, 4
    )


def format_number(n) -> str:
    if isinstance(n, float):
        return f"{n:,.1f}"
    return f"{n:,}"


def format_k(n: int) -> str:
    if n >= 1000000:
        return f"{n/1000000:.1f}m"
    elif n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def bar_chart(value: int, max_value: int, width: int = 10) -> str:
    """生成简易柱状图"""
    if max_value <= 0:
        return "░" * width
    filled = round(value / max_value * width)
    filled = min(filled, width)
    return "█" * filled + "░" * (width - filled)


def weighted_remaining_days(daily_data: list, remaining: int) -> str:
    """
    加权平均计算剩余天数
    daily_data: [(date_str, tokens), ...] 按日期降序
    """
    if not daily_data or remaining <= 0:
        return "N/A"

    now_tokens = sum(t for _, t in daily_data[:3]) / min(3, len(daily_data)) if len(daily_data) >= 1 else 0
    week_tokens = sum(t for _, t in daily_data[:7]) / min(7, len(daily_data)) if len(daily_data) >= 3 else 0
    month_tokens = sum(t for _, t in daily_data) / len(daily_data) if daily_data else 0

    # 加权：近3天60% + 近7天30% + 近30天10%
    weights_sum = 0
    weighted_daily = 0
    if len(daily_data) >= 1 and now_tokens > 0:
        weighted_daily += now_tokens * 0.6
        weights_sum += 0.6
    if len(daily_data) >= 3 and week_tokens > 0:
        weighted_daily += week_tokens * 0.3
        weights_sum += 0.3
    if daily_data and month_tokens > 0:
        weighted_daily += month_tokens * 0.1
        weights_sum += 0.1

    if weights_sum > 0:
        daily_avg = weighted_daily / weights_sum
    else:
        daily_avg = month_tokens

    if daily_avg > 0:
        return str(round(remaining / daily_avg, 1))
    return "N/A"


def check_alerts(used: int, total: int, thresholds: list) -> list:
    """检查告警阈值"""
    alerts = []
    if total <= 0:
        return alerts
    pct = used / total * 100
    for t in sorted(thresholds, reverse=True):
        if pct >= t:
            if t >= 95:
                alerts.append({"level": "critical", "threshold": t, "pct": round(pct, 1),
                               "msg": f"🔴 Credit 使用率 {pct:.1f}%，已超过 {t}% 阈值！建议立即补充额度"})
            elif t >= 80:
                alerts.append({"level": "warning", "threshold": t, "pct": round(pct, 1),
                               "msg": f"⚠️  Credit 使用率 {pct:.1f}%，已超过 {t}% 阈值，请关注消耗速度"})
    return alerts


def generate_report(
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    used_credit: int,
    total_credit: int,
    avg_daily_credit: float,
    model: str = "unknown",
    cache_pct: float = 0.0,
    context_tokens: int = 0,
    context_max: int = 0,
    session_count: int = 0,
    daily_data: list = None,
    top_sessions: list = None,
    warn_thresholds: list = None,
) -> str:
    rate = detect_rate(model)
    symbol = "¥" if rate["unit"] == "CNY" else "$"

    session_cost = calc_session_cost(input_tokens, output_tokens, rate)
    total_cost = calc_total_cost(total_tokens, input_tokens, output_tokens, rate)

    remaining = total_credit - used_credit
    usage_pct = round(used_credit / total_credit * 100, 1) if total_credit else 0
    context_pct = round(context_tokens / context_max * 100, 1) if context_max else 0

    # 加权剩余天数
    if daily_data:
        remaining_days = weighted_remaining_days(daily_data, remaining)
    else:
        remaining_days = round(remaining / avg_daily_credit, 1) if avg_daily_credit and avg_daily_credit > 0 else "N/A"

    lines = [
        f"📊 成本与额度报告",
        f"🧠 模型: {model}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🔹 当前会话",
        f"   📥 输入: {format_number(input_tokens)}  📤 输出: {format_number(output_tokens)}",
        f"   💾 缓存: {cache_pct:.0f}%  📚 上下文: {format_k(context_tokens)}/{format_k(context_max)} ({context_pct}%)",
        f"   💰 费用: {symbol}{session_cost}",
    ]

    # 告警
    if warn_thresholds:
        alerts = check_alerts(used_credit, total_credit, warn_thresholds)
        for a in alerts:
            lines.append(f"")
            lines.append(f"   {a['msg']}")

    lines.append(f"")
    lines.append(f"📅 今日累计 ({session_count} 会话): {symbol}{total_cost} (≈ {format_number(total_tokens)} Credit)")
    lines.append(f"📊 近 10 会话平均: {format_number(int(avg_daily_credit))} tokens/会话")

    # 近 7 天趋势
    if daily_data and len(daily_data) > 0:
        lines.append(f"")
        lines.append(f"📈 近 {min(len(daily_data), 7)} 天消耗趋势")
        max_tokens = max(t for _, t in daily_data[:7]) if daily_data else 1
        for date_str, tokens in daily_data[:7]:
            bar = bar_chart(tokens, max_tokens, 12)
            lines.append(f"   {date_str}  {bar}  {format_number(tokens)} tokens")

    # Top 烧钱会话
    if top_sessions and len(top_sessions) > 0:
        lines.append(f"")
        lines.append(f"🔥 最近会话消耗 Top {min(len(top_sessions), 5)}")
        for i, (sid, tokens, cost) in enumerate(top_sessions[:5]):
            short_id = sid[:12] + "…" if len(sid) > 12 else sid
            lines.append(f"   {i+1}. {short_id:<16} {format_number(tokens):>10} tokens  {symbol}{cost:.4f}")

    lines.append(f"")
    lines.append(f"💳 Credit")
    lines.append(f"   已用: {format_number(used_credit)} / {format_number(total_credit)} ({usage_pct}%)")
    lines.append(f"   ⏳ 预计可用: {remaining_days} 天")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def list_models():
    print("📋 支持的模型费率：")
    print(f"{'模型':<20} {'输入/1k':<12} {'输出/1k':<12}")
    print("─" * 44)
    for name, rate in MODEL_RATES.items():
        print(f"{name:<20} ¥{rate['input']:<11} ¥{rate['output']:<11}")
    print(f"\n默认费率: ¥{DEFAULT_RATE['input']}/1k 输入, ¥{DEFAULT_RATE['output']}/1k 输出")


def main():
    parser = argparse.ArgumentParser(description="MiMo Token Cost Calculator v2.1")
    parser.add_argument("--input", type=int, help="输入 tokens")
    parser.add_argument("--output", type=int, help="输出 tokens")
    parser.add_argument("--total", type=int, help="累计总 tokens")
    parser.add_argument("--used", type=int, help="已用 credit")
    parser.add_argument("--credit", type=int, help="总 credit 额度")
    parser.add_argument("--avg", type=float, help="日均消耗")
    parser.add_argument("--model", default="unknown", help="模型名称")
    parser.add_argument("--cache-pct", type=float, default=0, help="缓存命中率")
    parser.add_argument("--context", type=int, default=0, help="当前上下文 tokens")
    parser.add_argument("--context-max", type=int, default=0, help="最大上下文 tokens")
    parser.add_argument("--session-count", type=int, default=1, help="今日会话数")
    parser.add_argument("--daily", type=str, default="", help="近7天每日消耗 (JSON: [[date,tokens],...])")
    parser.add_argument("--top-sessions", type=str, default="", help="Top会话消耗 (JSON: [[id,tokens,cost],...])")
    parser.add_argument("--warn", type=str, default="80,95", help="告警阈值 (逗号分隔, 如 80,95)")
    parser.add_argument("--list-models", action="store_true", help="列出支持的模型费率")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # 兼容旧的位置参数
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        if len(sys.argv) >= 7:
            try:
                vals = [int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]),
                        int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6])]
                model = sys.argv[7] if len(sys.argv) > 7 else "unknown"
                report = generate_report(
                    vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], model
                )
                print(report)
                return
            except (ValueError, IndexError):
                pass
        print("Usage: cost.py <input> <output> <total> <used> <credit> <avg> [model]")
        sys.exit(1)

    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    required = ["input", "output", "total", "used", "credit", "avg"]
    missing = [f"--{r}" for r in required if getattr(args, r) is None]
    if missing:
        parser.error(f"缺少必需参数: {', '.join(missing)}")

    if args.input < 0 or args.output < 0:
        parser.error("tokens 数量不能为负数")
    if args.credit <= 0:
        parser.error("总 credit 额度必须大于 0")

    # 解析 daily data
    daily_data = []
    if args.daily:
        try:
            raw = json.loads(args.daily)
            daily_data = [(str(d[0]), int(d[1])) for d in raw]
        except (json.JSONDecodeError, IndexError, TypeError):
            parser.error("--daily 格式错误，应为 JSON: [[date,tokens],...]")

    # 解析 top sessions
    top_sessions = []
    if args.top_sessions:
        try:
            raw = json.loads(args.top_sessions)
            top_sessions = [(str(d[0]), int(d[1]), float(d[2])) for d in raw]
        except (json.JSONDecodeError, IndexError, TypeError):
            parser.error("--top-sessions 格式错误，应为 JSON: [[id,tokens,cost],...]")

    # 解析告警阈值
    warn_thresholds = []
    if args.warn:
        try:
            warn_thresholds = [int(x.strip()) for x in args.warn.split(",") if x.strip()]
        except ValueError:
            parser.error("--warn 格式错误，应为逗号分隔的整数")

    report = generate_report(
        input_tokens=args.input,
        output_tokens=args.output,
        total_tokens=args.total,
        used_credit=args.used,
        total_credit=args.credit,
        avg_daily_credit=args.avg,
        model=args.model,
        cache_pct=args.cache_pct,
        context_tokens=args.context,
        context_max=args.context_max,
        session_count=args.session_count,
        daily_data=daily_data,
        top_sessions=top_sessions,
        warn_thresholds=warn_thresholds,
    )

    if args.json:
        rate = detect_rate(args.model)
        session_cost = calc_session_cost(args.input, args.output, rate)
        remaining = args.credit - args.used
        usage_pct = round(args.used / args.credit * 100, 1) if args.credit else 0
        alerts = check_alerts(args.used, args.credit, warn_thresholds) if warn_thresholds else []
        r_days = weighted_remaining_days(daily_data, remaining) if daily_data else (
            round(remaining / args.avg, 1) if args.avg > 0 else None)

        result = {
            "model": args.model,
            "session": {"input": args.input, "output": args.output, "cost": session_cost},
            "today": {"total_tokens": args.total, "session_count": args.session_count},
            "credit": {"used": args.used, "total": args.credit,
                       "remaining": remaining, "usage_pct": usage_pct},
            "remaining_days": r_days,
            "trend": [{"date": d, "tokens": t} for d, t in daily_data[:7]],
            "top_sessions": [{"id": s, "tokens": t, "cost": c} for s, t, c in top_sessions[:5]],
            "alerts": alerts,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(report)


if __name__ == "__main__":
    main()
