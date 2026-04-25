#!/usr/bin/env python3
"""MiMo ASR — 语音识别脚本。

API: https://api.xiaomimimo.com/v1 (OpenAI 兼容格式)

Requires:
    pip install openai
    export MIMO_ASR_KEY=...  (或 MIMO_API_KEY)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from openai import OpenAI


def parse_args():
    parser = argparse.ArgumentParser(description="MiMo ASR 语音识别")
    parser.add_argument("audio", nargs="?", help="音频文件路径")
    parser.add_argument("--audio", dest="audio_kw", help="音频文件路径")
    parser.add_argument("-o", "--output", default="stdout",
                        help="输出路径（默认 stdout）")
    parser.add_argument("--lang", default="auto",
                        choices=["auto", "zh", "en", "ja", "ko"],
                        help="语言")
    parser.add_argument("--format", default="text",
                        choices=["text", "json", "srt"],
                        help="输出格式")
    parser.add_argument("--preprocess", action="store_true",
                        help="音频预处理（采样率/静音裁剪）")
    parser.add_argument("--no-diarization", action="store_true",
                        help="关闭说话人分离")
    parser.add_argument("--boost-cn", action="store_true",
                        help="增强中文解码")
    parser.add_argument("--chunk", type=int, default=0,
                        help="长音频分片秒数（0=不分片）")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="最大重试次数")
    return parser.parse_args()


def build_client():
    api_key = os.environ.get("MIMO_ASR_KEY") or os.environ.get("MIMO_API_KEY")
    if not api_key:
        print("Error: MIMO_ASR_KEY (或 MIMO_API_KEY) 未设置", file=sys.stderr)
        print("申请 Key: https://platform.xiaomimimo.com", file=sys.stderr)
        sys.exit(1)
    return OpenAI(api_key=api_key, base_url="https://api.xiaomimimo.com/v1")


def preprocess_audio(input_path):
    """音频预处理：统一 16k 采样率、单声道、静音裁剪"""
    output_path = input_path + ".preprocessed.wav"
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
        "-af", "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,"
               "areverse,silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,areverse",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"Warning: 预处理失败，使用原始文件: {result.stderr.decode()}", file=sys.stderr)
        return input_path
    return output_path


def chunk_audio(input_path, chunk_sec):
    """长音频分片"""
    from pathlib import Path
    import subprocess

    # 获取时长
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_path],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip())
    chunks = []
    base = Path(input_path).stem
    chunk_dir = Path(input_path).parent / f"{base}_chunks"
    chunk_dir.mkdir(exist_ok=True)

    for i, start in enumerate(range(0, int(duration), chunk_sec)):
        out = chunk_dir / f"chunk_{i:03d}.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-ss", str(start), "-t", str(chunk_sec),
            "-ar", "16000", "-ac", "1",
            str(out),
        ], capture_output=True)
        chunks.append(str(out))

    return chunks


def transcribe_file(client, audio_path, args):
    """转录单个文件"""
    lang_map = {"auto": None, "zh": "zh", "en": "en", "ja": "ja", "ko": "ko"}
    language = lang_map.get(args.lang)

    for attempt in range(args.max_retries):
        try:
            with open(audio_path, "rb") as f:
                kwargs = {
                    "model": "mimo-v2.5-asr",
                    "file": f,
                    "response_format": "verbose_json" if args.format in ("json", "srt") else "text",
                }
                if language:
                    kwargs["language"] = language

                result = client.audio.transcriptions.create(**kwargs)

            if args.format == "text":
                return result.text if hasattr(result, "text") else str(result)
            elif args.format == "json":
                return json.dumps(
                    {"text": result.text, "segments": getattr(result, "segments", [])},
                    ensure_ascii=False, indent=2,
                )
            elif args.format == "srt":
                return to_srt(getattr(result, "segments", []))

        except Exception as e:
            if "429" in str(e) and attempt < args.max_retries - 1:
                wait = 2 ** attempt
                print(f"[retry {attempt+1}/{args.max_retries}] Rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


def to_srt(segments):
    """将 segments 转为 SRT 格式"""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = format_time(seg.get("start", 0))
        end = format_time(seg.get("end", 0))
        text = seg.get("text", "").strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def format_time(seconds):
    """秒数转 SRT 时间格式"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    args = parse_args()
    audio_path = args.audio_kw or args.audio
    if not audio_path:
        print("Error: 请提供音频文件路径", file=sys.stderr)
        sys.exit(1)
    if not Path(audio_path).exists():
        print(f"Error: 文件不存在: {audio_path}", file=sys.stderr)
        sys.exit(1)

    client = build_client()

    # 预处理
    if args.preprocess:
        audio_path = preprocess_audio(audio_path)

    # 分片处理
    if args.chunk and args.chunk > 0:
        chunks = chunk_audio(audio_path, args.chunk)
        results = []
        for chunk in chunks:
            print(f"[transcribing] {chunk}", file=sys.stderr)
            results.append(transcribe_file(client, chunk, args))
        text = "\n".join(results)
    else:
        text = transcribe_file(client, audio_path, args)

    # 输出
    if args.output == "stdout":
        print(text)
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        print(f"{output_path}")


if __name__ == "__main__":
    main()
