#!/usr/bin/env python3
"""MiMo TTS — 统一语音合成脚本 v2.99.92。

支持三款模型：tts（预置音色）/ voice-design（音色设计）/ voice-clone（音色克隆）
API: https://api.xiaomimimo.com/v1 (OpenAI 兼容格式)

无 MIMO_API_KEY 时自动 fallback 到 edge-tts（免费，无需 Key）

Features:
    - 防限流：随机延迟 + 最大并发限制
    - 长文本：自动智能分句分段合成
    - 缓存：相同文本零消耗
    - 异常捕获：网络波动自动重试，不闪退
    - 隐私：不打印 Key，临时文件自动清理
    - 开关：USE_CLOUD_TTS 一键切本地
    - 批量合成：--file 逐行读取批量处理
    - 格式自动检测：根据 -o 后缀推断格式
    - 默认预处理：数字/符号自动规范化（--no-preprocess 关闭）
    - 智能音色推荐：根据文本语言自动推荐
    - 质量自检：检测空文件/静音/过短
    - 目录监听：--watch 自动合成新增文件

Requires:
    pip install openai
    pip install edge-tts  (fallback)
    export MIMO_API_KEY=...  (可选，不设则走 edge-tts)
"""

import argparse
import asyncio
import base64
import hashlib
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CACHE_DIR = SCRIPT_DIR.parent / "cache"

# ============================================================
# 全局配置
# ============================================================

USE_CLOUD_TTS = True       # 改为 False 禁用云端，走本地/edge-tts
MAX_CONCURRENT = 2         # 最大并发数
REQUEST_INTERVAL = (0.3, 0.6)  # 请求间隔范围（秒）
TEXT_SPLIT_LIMIT = 120     # 长文本分句阈值（字符）

_run_count = 0
_run_lock = threading.Lock()

PRESET_VOICES = [
    "冰糖", "茉莉", "苏打", "白桦",
    "Mia", "Chloe", "Milo", "Dean",
]

# 全局固化音色参数
VOICE_PROFILES = {
    "冰糖": {"speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "茉莉": {"speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "苏打": {"speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "白桦": {"speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "Mia":  {"speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "Chloe": {"speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "Milo": {"speed": 1.0, "pitch": 0, "emotion": "neutral"},
    "Dean": {"speed": 1.0, "pitch": 0, "emotion": "neutral"},
}

EDGE_VOICE_MAP = {
    "冰糖": "zh-CN-XiaoyiNeural",
    "茉莉": "zh-CN-XiaochenNeural",
    "苏打": "zh-CN-YunxiNeural",
    "白桦": "zh-CN-YunjianNeural",
    "Mia": "en-US-JennyNeural",
    "Chloe": "en-US-AriaNeural",
    "Milo": "en-US-GuyNeural",
    "Dean": "en-US-DavisNeural",
}

MODEL_MAP = {
    "tts": "mimo-v2.5-tts",
    "voice-design": "mimo-v2.5-tts-voicedesign",
    "voice-clone": "mimo-v2.5-tts-voiceclone",
}


# ============================================================
# 工具函数
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description="MiMo TTS 统一语音合成")
    parser.add_argument("text", nargs="?", help="要合成的文本（也可用 --text）")
    parser.add_argument("--text", dest="text_kw", help="要合成的文本")
    parser.add_argument("-o", "--output", default="output.wav", help="输出路径")
    parser.add_argument("-m", "--model", default="tts",
                        choices=["tts", "voice-design", "voice-clone"],
                        help="模型选择")
    parser.add_argument("-v", "--voice", default="冰糖",
                        help="预置音色 ID（仅 tts 模型）")
    parser.add_argument("-s", "--style", default="",
                        help="风格标签，如 '开心 变快'")
    parser.add_argument("-f", "--format", default=None,
                        choices=["wav", "mp3", "ogg"],
                        help="输出格式（默认根据 -o 后缀自动推断）")
    parser.add_argument("--file", default=None,
                        help="批量合成：文本文件路径（每行一段文本）")
    parser.add_argument("--no-preprocess", action="store_true",
                        help="关闭文本预处理（默认开启）")
    parser.add_argument("--watch", default=None,
                        help="监听目录，自动合成新增 .txt 文件")
    parser.add_argument("--recommend-voice", action="store_true",
                        help="根据文本内容智能推荐音色")
    parser.add_argument("--voice-desc", default="",
                        help="VoiceDesign 音色描述（voice-design 模型）")
    parser.add_argument("--ref-audio", default="",
                        help="VoiceClone 参考音频路径（voice-clone 模型）")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="语速（预留参数）")
    parser.add_argument("--pitch", type=float, default=1.0,
                        help="音调（预留参数）")
    parser.add_argument("--preprocess", action="store_true", default=True,
                        help="开启文本预处理（默认开启，用 --no-preprocess 关闭）")
    parser.add_argument("--denoise", action="store_true",
                        help="后置降噪")
    parser.add_argument("--normalize", action="store_true",
                        help="音量归一化")
    parser.add_argument("--cache", action="store_true",
                        help="音频缓存")
    parser.add_argument("--optimize", choices=["gpu", "cpu", "lite"],
                        help="推理优化模式（预留参数）")
    parser.add_argument("--list-voices", action="store_true",
                        help="列出可用音色")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="最大重试次数")
    return parser.parse_args()


def list_voices():
    print("=== MiMo 预置音色 ===")
    print(f"{'音色':<8} {'语言':<6} {'性别':<4} {'风格':<20} {'推荐场景'}")
    print("-" * 60)
    voices_info = [
        ("冰糖", "中文", "女", "活泼少女，清脆甜美", "日常/欢快/少女角色"),
        ("茉莉", "中文", "女", "知性女声，温柔稳重", "叙述/有声书/温柔场景"),
        ("苏打", "中文", "男", "阳光少年，活力朝气", "播报/活力/少年角色"),
        ("白桦", "中文", "男", "成熟男声，沉稳大气", "新闻/正式/成熟角色"),
        ("Mia", "EN", "F", "Lively girl", "English daily/casual"),
        ("Chloe", "EN", "F", "Witty Grace", "English narration"),
        ("Milo", "EN", "M", "Sunny boy", "English energetic"),
        ("Dean", "EN", "M", "Steady Gentle", "English formal"),
    ]
    for name, lang, gender, style, scene in voices_info:
        print(f"  {name:<6} {lang:<6} {gender:<4} {style:<18} {scene}")
    print()
    print("=== edge-tts 备选音色（免费，无需 Key）===")
    print("  zh-CN-XiaoyiNeural    活泼少女")
    print("  zh-CN-XiaochenNeural  知性女声")
    print("  zh-CN-YunxiNeural     阳光少年")
    print("  zh-CN-YunjianNeural   成熟男声")
    print("  en-US-JennyNeural     Lively girl")
    print("  en-US-AriaNeural      Witty Grace")
    print("  en-US-GuyNeural       Sunny boy")
    print("  en-US-DavisNeural     Steady Gentle")
    print()
    print("=== 智能推荐 ===")
    print("  使用 --recommend-voice 根据文本内容自动选择最佳音色")
    print("  支持情感检测：开心→冰糖/Mia，悲伤→茉莉/Chloe，严肃→白桦/Dean")
    print()
    print("使用 edge-tts: 不设 MIMO_API_KEY 自动走免费通道")


def check_ffmpeg():
    return shutil.which("ffmpeg") is not None


def preprocess_text(text):
    """文本预处理：分句、清洗、数字替换"""
    text = text.replace(",", "，").replace(".", "。")
    text = text.replace("!", "！").replace("?", "？")
    text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、；：""''（）《》-]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    def num_to_cn(m):
        n = int(m.group())
        if n == 0:
            return "零"
        digits = "零一二三四五六七八九"
        units = ["", "十", "百", "千"]
        result = ""
        s = str(n)
        for i, d in enumerate(s):
            pos = len(s) - i - 1
            if d != '0':
                result += digits[int(d)] + units[pos]
            elif result and result[-1] != '零':
                result += "零"
        return result.rstrip("零")

    text = re.sub(r'\b\d+\b', num_to_cn, text)
    return text


def split_text(text, limit=TEXT_SPLIT_LIMIT):
    """智能分句：按标点切分，每段不超过 limit 字符"""
    sp = ["。", "！", "？", "；", "，", ".", "!", "?", ";", ","]
    res = []
    tmp = ""
    for ch in text:
        tmp += ch
        if len(tmp) >= limit and ch in sp:
            res.append(tmp.strip())
            tmp = ""
    if tmp.strip():
        res.append(tmp.strip())
    return [s for s in res if s]


def get_cache_key(text, voice, model, style):
    raw = f"{text}:{voice}:{model}:{style}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached_audio(text, voice, model, style):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = get_cache_key(text, voice, model, style)
    path = CACHE_DIR / f"{key}.wav"
    return path if path.exists() else None


def save_cache(text, voice, model, style, src_path):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = get_cache_key(text, voice, model, style)
    dst = CACHE_DIR / f"{key}.wav"
    shutil.copy(str(src_path), str(dst))


def rate_limit_delay():
    """随机延迟防风控"""
    delay = REQUEST_INTERVAL[0] + random.uniform(0, REQUEST_INTERVAL[1] - REQUEST_INTERVAL[0])
    time.sleep(delay)


def postprocess_audio(wav_path, args):
    """后处理：降噪、归一化、格式转换"""
    if not args.denoise and not args.normalize and args.format == "wav":
        return

    if not check_ffmpeg():
        print("⚠️  ffmpeg 未安装，跳过后处理", file=sys.stderr)
        print("   安装: apt install ffmpeg / brew install ffmpeg", file=sys.stderr)
        return

    tmp_path = wav_path + ".tmp.wav"
    cmd = ["ffmpeg", "-y", "-i", wav_path]

    filters = []
    if args.denoise:
        filters.append("afftdn=nf=-20")
    if args.normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    if filters:
        cmd += ["-af", ",".join(filters)]

    if args.format != "wav":
        if args.format == "mp3":
            cmd += ["-codec:a", "libmp3lame", "-b:a", "192k"]
        elif args.format == "ogg":
            cmd += ["-codec:a", "libvorbis", "-b:a", "192k"]
        out_path = wav_path.rsplit(".", 1)[0] + "." + args.format
    else:
        out_path = wav_path

    if out_path != wav_path:
        cmd.append(out_path)
    else:
        cmd.append(tmp_path)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️  后处理失败: {result.stderr[:200]}", file=sys.stderr)
        return

    if out_path == wav_path:
        os.replace(tmp_path, wav_path)


def encode_voice_file(file_path):
    """编码音色样本为 DataURL"""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: 音频文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)
    suffix = path.suffix.lower()
    mime_map = {".mp3": "audio/mpeg", ".wav": "audio/wav"}
    mime_type = mime_map.get(suffix)
    if not mime_type:
        print(f"Error: 不支持的格式 {suffix}，请使用 mp3 或 wav", file=sys.stderr)
        sys.exit(1)
    data = path.read_bytes()
    if len(data) > 10 * 1024 * 1024:
        print("Error: 音频文件超过 10MB 限制", file=sys.stderr)
        sys.exit(1)
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def concat_wav_files(wav_files, output_path):
    """用 ffmpeg 拼接多个 wav 文件"""
    if not check_ffmpeg():
        # 无 ffmpeg 则用二进制拼接（仅限同格式）
        with open(output_path, "wb") as out:
            for f in wav_files:
                out.write(Path(f).read_bytes())
        return

    list_file = output_path + ".list.txt"
    with open(list_file, "w") as f:
        for wav in wav_files:
            f.write(f"file '{wav}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path],
        capture_output=True,
    )
    os.remove(list_file)


def cleanup_temp(*paths):
    """安全删除临时文件"""
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


def detect_format(output_path):
    """根据输出文件后缀自动推断格式"""
    ext = Path(output_path).suffix.lower()
    fmt_map = {".wav": "wav", ".mp3": "mp3", ".ogg": "ogg"}
    return fmt_map.get(ext, "wav")


def recommend_voice(text):
    """根据文本内容智能推荐音色"""
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    total = cn_chars + en_chars
    if total == 0:
        return "冰糖"

    cn_ratio = cn_chars / total if total > 0 else 0

    # 检测情感关键词
    happy_words = ["开心", "高兴", "快乐", "哈哈", "恭喜", "太好了", "happy", "great", "wonderful"]
    sad_words = ["伤心", "难过", "悲伤", "遗憾", "可惜", "sorry", "sad", "unfortunately"]
    angry_words = ["生气", "愤怒", "讨厌", "可恶", "angry", "hate"]
    serious_words = ["重要", "注意", "警告", "危险", "warning", "danger", "important"]

    text_lower = text.lower()
    if any(w in text_lower for w in happy_words):
        return "冰糖" if cn_ratio > 0.5 else "Mia"
    if any(w in text_lower for w in sad_words):
        return "茉莉" if cn_ratio > 0.5 else "Chloe"
    if any(w in text_lower for w in angry_words):
        return "苏打" if cn_ratio > 0.5 else "Milo"
    if any(w in text_lower for w in serious_words):
        return "白桦" if cn_ratio > 0.5 else "Dean"

    # 默认按语言推荐
    if cn_ratio > 0.7:
        return "冰糖"
    elif cn_ratio < 0.3:
        return "Mia"
    else:
        return "茉莉"


def quality_check(output_path):
    """合成后质量自检"""
    path = Path(output_path)
    if not path.exists():
        print(f"❌ 质量检查失败：文件不存在 {output_path}", file=sys.stderr)
        return False

    size = path.stat().st_size
    if size == 0:
        print(f"❌ 质量检查失败：文件为空 {output_path}", file=sys.stderr)
        return False

    if size < 1000:  # 小于 1KB 可能是静音
        print(f"⚠️  质量警告：文件过小 ({size} bytes)，可能为静音 {output_path}", file=sys.stderr)
        return True  # 不算失败，只是警告

    # 检查 WAV 头
    if output_path.endswith(".wav"):
        with open(output_path, "rb") as f:
            header = f.read(4)
            if header != b"RIFF":
                print(f"⚠️  质量警告：WAV 文件头异常 {output_path}", file=sys.stderr)

    return True


def synthesize_single(text, args, client=None):
    """单段文本合成（供批量和 watch 模式复用）"""
    if args.preprocess and not args.no_preprocess:
        text = preprocess_text(text)

    # 缓存检查
    cache_key_text = text
    if args.style:
        cache_key_text = f"({args.style}){text}"
    if args.cache:
        cached = get_cached_audio(cache_key_text, args.voice, args.model, args.style)
        if cached:
            shutil.copy(str(cached), args.output)
            print(f"[cache hit] {args.output}")
            return True

    # 尝试 MiMo API
    if client is None and USE_CLOUD_TTS:
        client = build_mimo_client()
    if client:
        success = synthesize_mimo_client(client, text, args)
        if success:
            if args.cache:
                save_cache(cache_key_text, args.voice, args.model, args.style, args.output)
            quality_check(args.output)
            return True
        print("MiMo API 失败，尝试 edge-tts fallback...", file=sys.stderr)

    if args.model == "voice-clone":
        print("Error: voice-clone 需要 MiMo API Key", file=sys.stderr)
        return False

    success = synthesize_edge_tts(text, args)
    if success:
        if args.cache:
            save_cache(cache_key_text, args.voice, args.model, args.style, args.output)
        quality_check(args.output)
    return success


def synthesize_mimo_client(client, text, args):
    """直接调用 MiMo API（不经过 synthesize_mimo 的 full_text 包装）"""
    model_id = MODEL_MAP[args.model]
    messages = []

    if args.model == "tts":
        if args.style:
            messages.append({"role": "user", "content": f"用{args.style}的风格"})
        messages.append({"role": "assistant", "content": text})
        audio_opts = {"audio": {"format": "wav", "voice": args.voice}}
    elif args.model == "voice-design":
        context = args.voice_desc or args.style
        if not context:
            print("Error: voice-design 模型需要 --voice-desc 或 -s 参数", file=sys.stderr)
            return False
        messages.append({"role": "user", "content": context})
        messages.append({"role": "assistant", "content": text})
        audio_opts = {"audio": {"format": "wav"}}
    elif args.model == "voice-clone":
        if not args.ref_audio:
            print("Error: voice-clone 模型需要 --ref-audio 参数", file=sys.stderr)
            return False
        voice_data = encode_voice_file(args.ref_audio)
        if args.style:
            messages.append({"role": "user", "content": f"用{args.style}的风格"})
        messages.append({"role": "assistant", "content": text})
        audio_opts = {"audio": {"format": "wav", "voice": voice_data}}

    fmt = args.format or "wav"
    if fmt != "wav":
        audio_opts["audio"]["format"] = fmt

    # 长文本分段
    chunks = split_text(text)
    if len(chunks) <= 1:
        audio_bytes = _mimo_call(client, {"messages": messages, "model": model_id}, audio_opts, args.max_retries)
        if audio_bytes:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_bytes)
            postprocess_audio(str(output_path), args)
            print(f"{output_path}")
            return True
        return False

    # 多段合成
    print(f"[长文本] 分 {len(chunks)} 段合成...", file=sys.stderr)
    temp_files = []
    for i, chunk in enumerate(chunks):
        print(f"  [{i+1}/{len(chunks)}] {chunk[:30]}...", file=sys.stderr)
        msgs = list(messages)
        msgs[-1] = {"role": "assistant", "content": chunk}

        audio_bytes = _mimo_call(client, {"messages": msgs, "model": model_id}, audio_opts, args.max_retries)
        if not audio_bytes:
            print(f"  ⚠️ 第 {i+1} 段失败", file=sys.stderr)
            cleanup_temp(*temp_files)
            return False

        tmp = str(CACHE_DIR / f"_chunk_{i}.wav")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        Path(tmp).write_bytes(audio_bytes)
        temp_files.append(tmp)

    concat_wav_files(temp_files, args.output)
    postprocess_audio(args.output, args)
    cleanup_temp(*temp_files)
    print(f"{args.output} [{len(chunks)} 段拼接]")
    return True


def synthesize_batch(file_path, args):
    """批量合成：逐行读取文本文件"""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: 文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        print("Error: 文件为空", file=sys.stderr)
        sys.exit(1)

    print(f"[批量] 共 {len(lines)} 段文本", file=sys.stderr)

    # 智能推荐音色
    if args.recommend_voice:
        combined = " ".join(lines)
        recommended = recommend_voice(combined)
        print(f"[智能推荐] 音色: {recommended}", file=sys.stderr)
        args.voice = recommended

    client = build_mimo_client() if USE_CLOUD_TTS else None
    out_dir = Path(args.output).parent if args.output != "output.wav" else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.output).stem if args.output != "output.wav" else "output"

    fmt = args.format or detect_format(args.output)
    success_count = 0
    for i, line in enumerate(lines):
        out_path = str(out_dir / f"{stem}_{i+1:03d}.{fmt}")
        args_copy = argparse.Namespace(**vars(args))
        args_copy.output = out_path
        args_copy.format = fmt
        print(f"\n[{i+1}/{len(lines)}] {line[:50]}...", file=sys.stderr)
        if synthesize_single(line, args_copy, client):
            quality_check(out_path)
            success_count += 1

    print(f"\n[批量完成] {success_count}/{len(lines)} 成功", file=sys.stderr)


def watch_directory(watch_dir, args):
    """监听目录，自动合成新增 .txt 文件"""
    watch_path = Path(watch_dir)
    if not watch_path.is_dir():
        print(f"Error: 目录不存在: {watch_dir}", file=sys.stderr)
        sys.exit(1)

    processed = set()
    # 记录已有文件
    for f in watch_path.glob("*.txt"):
        processed.add(f.name)

    print(f"[watch] 监听目录: {watch_dir} (Ctrl+C 退出)", file=sys.stderr)
    client = build_mimo_client() if USE_CLOUD_TTS else None

    try:
        while True:
            for txt_file in sorted(watch_path.glob("*.txt")):
                if txt_file.name in processed:
                    continue
                processed.add(txt_file.name)
                text = txt_file.read_text(encoding="utf-8").strip()
                if not text:
                    continue

                fmt = args.format or "wav"
                out_path = str(txt_file.with_suffix(f".{fmt}"))
                args_copy = argparse.Namespace(**vars(args))
                args_copy.output = out_path
                args_copy.format = fmt

                print(f"\n[watch] 发现新文件: {txt_file.name}", file=sys.stderr)
                if synthesize_single(text, args_copy, client):
                    quality_check(out_path)
                    print(f"[watch] 完成: {out_path}", file=sys.stderr)

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[watch] 已退出", file=sys.stderr)


# ============================================================
# MiMo API 合成
# ============================================================

def build_mimo_client():
    from openai import OpenAI
    api_key = os.environ.get("MIMO_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.xiaomimimo.com/v1")


def _mimo_call(client, messages, audio_opts, max_retries):
    """单次 MiMo API 调用（带重试 + 限流）"""
    global _run_count

    for attempt in range(max_retries):
        # 并发限制
        with _run_lock:
            if _run_count >= MAX_CONCURRENT:
                print(f"⚠️  并发已达上限 ({MAX_CONCURRENT})，等待中...", file=sys.stderr)
                time.sleep(1)
                continue
            _run_count += 1

        try:
            rate_limit_delay()
            completion = client.chat.completions.create(**messages, **audio_opts)
            message = completion.choices[0].message
            if message.audio is None or not getattr(message.audio, "data", None):
                print("Error: API 未返回音频数据", file=sys.stderr)
                return None

            return base64.b64decode(message.audio.data)

        except Exception as e:
            err = str(e)
            if "429" in err:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"[retry {attempt+1}/{max_retries}] 429 限流，等待 {wait:.1f}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            elif any(code in err for code in ["502", "503", "timeout", "connection"]):
                wait = 1 + attempt
                print(f"[retry {attempt+1}/{max_retries}] 网络异常，等待 {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            else:
                print(f"MiMo API Error: {err[:200]}", file=sys.stderr)
                return None

        finally:
            with _run_lock:
                _run_count = max(0, _run_count - 1)

    print("Error: 超过最大重试次数", file=sys.stderr)
    return None


def synthesize_mimo(client, text, args):
    """MiMo API 合成（支持长文本自动分段）"""
    # 构建请求参数
    model_id = MODEL_MAP[args.model]
    messages = []

    if args.model == "tts":
        if args.style:
            messages.append({"role": "user", "content": f"用{args.style}的风格"})
        messages.append({"role": "assistant", "content": text})
        audio_opts = {"model": model_id, "audio": {"format": "wav", "voice": args.voice}}
    elif args.model == "voice-design":
        context = args.voice_desc or args.style
        if not context:
            print("Error: voice-design 模型需要 --voice-desc 或 -s 参数", file=sys.stderr)
            sys.exit(1)
        messages.append({"role": "user", "content": context})
        messages.append({"role": "assistant", "content": text})
        audio_opts = {"model": model_id, "audio": {"format": "wav"}}
    elif args.model == "voice-clone":
        if not args.ref_audio:
            print("Error: voice-clone 模型需要 --ref-audio 参数", file=sys.stderr)
            sys.exit(1)
        voice_data = encode_voice_file(args.ref_audio)
        if args.style:
            messages.append({"role": "user", "content": f"用{args.style}的风格"})
        messages.append({"role": "assistant", "content": text})
        audio_opts = {"model": model_id, "audio": {"format": "wav", "voice": voice_data}}

    # 长文本自动分段
    chunks = split_text(text)
    if len(chunks) <= 1:
        audio_bytes = _mimo_call(client, {"messages": messages, **{k: v for k, v in audio_opts.items() if k != "audio"}}, {"audio": audio_opts.get("audio", {})}, args.max_retries)
        if audio_bytes:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_bytes)
            postprocess_audio(str(output_path), args)
            print(f"{output_path}")
            return True
        return False

    # 多段合成
    print(f"[长文本] 分 {len(chunks)} 段合成...", file=sys.stderr)
    temp_files = []
    for i, chunk in enumerate(chunks):
        print(f"  [{i+1}/{len(chunks)}] {chunk[:30]}...", file=sys.stderr)
        msgs = list(messages)
        msgs[-1] = {"role": "assistant", "content": chunk}

        audio_bytes = _mimo_call(client, {"messages": msgs}, {"audio": audio_opts.get("audio", {})}, args.max_retries)
        if not audio_bytes:
            print(f"  ⚠️ 第 {i+1} 段失败", file=sys.stderr)
            cleanup_temp(*temp_files)
            return False

        tmp = str(CACHE_DIR / f"_chunk_{i}.wav")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        Path(tmp).write_bytes(audio_bytes)
        temp_files.append(tmp)

    # 拼接
    concat_wav_files(temp_files, args.output)
    postprocess_audio(args.output, args)
    cleanup_temp(*temp_files)
    print(f"{args.output} [{len(chunks)} 段拼接]")
    return True


# ============================================================
# edge-tts fallback 合成
# ============================================================

def synthesize_edge_tts(text, args):
    """edge-tts 免费合成（fallback）"""
    try:
        import edge_tts
    except ImportError:
        print("Error: edge-tts 未安装", file=sys.stderr)
        print("  pip install edge-tts", file=sys.stderr)
        sys.exit(1)

    voice = EDGE_VOICE_MAP.get(args.voice, "zh-CN-XiaoyiNeural")
    rate = int((args.speed - 1.0) * 100)
    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
    pitch = int((args.pitch - 1.0) * 100)
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"

    # 长文本分段
    chunks = split_text(text)
    if len(chunks) <= 1:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async def _generate():
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_str, pitch=pitch_str)
            await communicate.save(str(output_path))

        asyncio.run(_generate())
        postprocess_audio(str(output_path), args)
        print(f"{output_path} [edge-tts]")
        return True

    # 多段
    print(f"[长文本] 分 {len(chunks)} 段合成 (edge-tts)...", file=sys.stderr)
    temp_files = []
    for i, chunk in enumerate(chunks):
        print(f"  [{i+1}/{len(chunks)}] {chunk[:30]}...", file=sys.stderr)
        tmp = str(CACHE_DIR / f"_edge_chunk_{i}.wav")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        async def _gen_chunk(c=chunk, t=tmp):
            communicate = edge_tts.Communicate(text=c, voice=voice, rate=rate_str, pitch=pitch_str)
            await communicate.save(t)

        asyncio.run(_gen_chunk())
        temp_files.append(tmp)

    concat_wav_files(temp_files, args.output)
    postprocess_audio(args.output, args)
    cleanup_temp(*temp_files)
    print(f"{args.output} [edge-tts, {len(chunks)} 段拼接]")
    return True


# ============================================================
# 主逻辑
# ============================================================

def synthesize(args):
    text = args.text_kw or args.text
    if not text and not args.file and not args.watch:
        print("Error: 请提供要合成的文本、--file 或 --watch", file=sys.stderr)
        sys.exit(1)

    # 批量模式
    if args.file:
        synthesize_batch(args.file, args)
        return

    # 监听模式
    if args.watch:
        watch_directory(args.watch, args)
        return

    # 智能推荐音色
    if args.recommend_voice and text:
        recommended = recommend_voice(text)
        print(f"[智能推荐] 音色: {recommended}", file=sys.stderr)
        args.voice = recommended

    # 自动推断格式
    if args.format is None:
        args.format = detect_format(args.output)

    synthesize_single(text, args)


def main():
    args = parse_args()

    if args.list_voices:
        list_voices()
        return

    synthesize(args)


if __name__ == "__main__":
    main()
