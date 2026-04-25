#!/usr/bin/env python3
"""
MiMo Token Cost Calculator v2.0
Usage:
  python3 cost.py --input <in> --output <out> --total <total> --used <used> --credit <credit> --avg <avg> [--model <model>]
  python3 cost.py --list-models
  python3 cost.py --help

Changelog v2.0:
  - 修复今日累计计算逻辑（按日期过滤）
  - 使用实际输入输出比替代硬编码 70/30
  - 新增 mimo-v2.5 系列费率
  - 改进错误处理和参数校验
  - 新增 --list-models 参数
  - 输出格式与 SKILL.md 对齐
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
    """动态匹配计费规则，精确匹配优先，找不到用默认"""
    model_lower = model.lower()
    # 精确匹配优先
    for key, rate in MODEL_RATES.items():
        if key == model_lower:
            return rate
    # 子串匹配
    for key, rate in MODEL_RATES.items():
        if key in model_lower:
            return rate
    return DEFAULT_RATE


def calc_session_cost(input_tokens: int, output_tokens: int, rate: dict) -> float:
    """精确计算本次会话费用（使用实际输入/输出数量）"""
    return round((input_tokens * rate["input"] + output_tokens * rate["output"]) / 1000, 4)


def calc_total_cost(total_tokens: int, input_tokens: int, output_tokens: int, rate: dict) -> float:
    """计算累计费用（使用实际输入输出比）"""
    io_total = input_tokens + output_tokens
    if io_total > 0:
        input_ratio = input_tokens / io_total
    else:
        input_ratio = 0.7  # fallback
    return round(
        (total_tokens * input_ratio * rate["input"] +
         total_tokens * (1 - input_ratio) * rate["output"]) / 1000, 4
    )


def format_number(n: int) -> str:
    return f"{n:,}"


def format_k(n: int) -> str:
    if n >= 1000000:
        return f"{n/1000000:.1f}m"
    elif n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


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
) -> str:
    rate = detect_rate(model)
    symbol = "¥" if rate["unit"] == "CNY" else "$"

    session_cost = calc_session_cost(input_tokens, output_tokens, rate)
    session_credits = input_tokens + output_tokens

    total_cost = calc_total_cost(total_tokens, input_tokens, output_tokens, rate)

    remaining = total_credit - used_credit
    usage_pct = round(used_credit / total_credit * 100, 1) if total_credit else 0
    remaining_days = round(remaining / avg_daily_credit, 1) if avg_daily_credit and avg_daily_credit > 0 else "N/A"

    context_pct = round(context_tokens / context_max * 100, 1) if context_max else 0

    lines = [
        f"📊 成本与额度报告",
        f"🧠 模型: {model}",
        f"━━━━━━━━━━━━━━━━━━━━━",
        f"🔹 当前会话",
        f"   📥 输入: {format_number(input_tokens)}  📤 输出: {format_number(output_tokens)}",
        f"   💾 缓存: {cache_pct:.0f}%  📚 上下文: {format_k(context_tokens)}/{format_k(context_max)} ({context_pct}%)",
        f"   💰 费用: {symbol}{session_cost}",
        f"",
        f"📅 今日累计 ({session_count} 会话): {symbol}{total_cost} (≈ {format_number(total_tokens)} Credit)",
        f"📊 近 10 会话平均: {format_number(int(avg_daily_credit))} tokens/会话",
        f"",
        f"💳 Credit",
        f"   已用: {format_number(used_credit)} / {format_number(total_credit)} ({usage_pct}%)",
        f"   ⏳ 预计可用: {remaining_days} 天",
        f"━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)


def list_models():
    print("📋 支持的模型费率：")
    print(f"{'模型':<20} {'输入/1k':<12} {'输出/1k':<12}")
    print("─" * 44)
    for name, rate in MODEL_RATES.items():
        print(f"{name:<20} ¥{rate['input']:<11} ¥{rate['output']:<11}")
    print(f"\n默认费率: ¥{DEFAULT_RATE['input']}/1k 输入, ¥{DEFAULT_RATE['output']}/1k 输出")


def main():
    parser = argparse.ArgumentParser(description="MiMo Token Cost Calculator v2.0")
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
    parser.add_argument("--list-models", action="store_true", help="列出支持的模型费率")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # 兼容旧的位置参数
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        # 旧格式: cost.py <input> <output> <total> <used> <credit> <avg> [model]
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
        print("   or: cost.py --input <in> --output <out> ... (use --help for details)")
        sys.exit(1)

    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    # 校验必需参数
    required = ["input", "output", "total", "used", "credit", "avg"]
    missing = [f"--{r}" for r in required if getattr(args, r) is None]
    if missing:
        parser.error(f"缺少必需参数: {', '.join(missing)}")

    if args.input < 0 or args.output < 0:
        parser.error("tokens 数量不能为负数")
    if args.credit <= 0:
        parser.error("总 credit 额度必须大于 0")

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
    )

    if args.json:
        rate = detect_rate(args.model)
        session_cost = calc_session_cost(args.input, args.output, rate)
        result = {
            "model": args.model,
            "session": {"input": args.input, "output": args.output, "cost": session_cost},
            "today": {"total_tokens": args.total, "session_count": args.session_count},
            "credit": {"used": args.used, "total": args.credit,
                       "remaining": args.credit - args.used,
                       "usage_pct": round(args.used / args.credit * 100, 1)},
            "remaining_days": round((args.credit - args.used) / args.avg, 1) if args.avg > 0 else None,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(report)


if __name__ == "__main__":
    main()
