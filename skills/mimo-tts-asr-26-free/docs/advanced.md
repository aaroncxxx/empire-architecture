# MiMo TTS & ASR — 进阶优化

本文档包含推理性能、音质调优、工程化部署等高级内容。基础用法见 `SKILL.md`。

## ⚡ 推理性能优化

### GPU 优化

```python
# 1. 半精度推理 — 显存减半、速度翻倍
model = AutoModelForCausalLM.from_pretrained(
    "XiaomiMiMo/MiMo-V2.5-TTS",
    torch_dtype=torch.float16,
    device_map="auto"
)

# 2. CUDA 流异步推理
stream = torch.cuda.Stream()
with torch.cuda.stream(stream):
    output = model.generate(input_ids, **kwargs)
stream.synchronize()

# 3. 关闭梯度计算
with torch.no_grad():
    output = model.generate(input_ids, **kwargs)
```

快捷方式：
```bash
python3 "{baseDir}/scripts/tts.py" "你好" --optimize gpu -o output.wav
```

### CPU 优化（无独显）

```python
# 1. ONNX Runtime INT8 量化（速度 +40%~60%）
import onnxruntime as ort
session = ort.InferenceSession("model_quant.onnx", providers=["CPUExecutionProvider"])

# 2. CPU 线程绑定
import os
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["KMP_AFFINITY"] = "granularity=fine,compact,1,0"
```

快捷方式：
```bash
python3 "{baseDir}/scripts/tts.py" "你好" --optimize cpu -o output.wav
```

### 模型参数调优

```python
# 采样步数 50→20（速度 2.5x）
output = model.generate(input_ids, num_inference_steps=20, denoising_strength=0.5)

# 关闭情感/风格分支
output = model.generate(input_ids, emotion_prediction=False, style_branch=False)
```

轻量模式：
```bash
python3 "{baseDir}/scripts/tts.py" "你好" --optimize lite -o output.wav
```

## 🎵 音质优化

### 文本预处理

```python
import re

def smart_split(text, max_len=200):
    """按标点智能分句"""
    sentences = re.split(r'([。！？；\.\!\?\;])', text)
    chunks, current = [], ""
    for i in range(0, len(sentences), 2):
        seg = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
        if len(current) + len(seg) > max_len and current:
            chunks.append(current)
            current = seg
        else:
            current += seg
    if current:
        chunks.append(current)
    return chunks

def clean_text(text):
    """统一标点，过滤特殊字符"""
    text = text.replace(",", "，").replace(".", "。").replace("!", "！").replace("?", "？")
    text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、；：""''（）《》\-]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def normalize_text(text):
    """数字转中文，英文加空格"""
    def num_to_cn(m):
        n = int(m.group())
        units = ["", "十", "百", "千"]
        digits = "零一二三四五六七八九"
        if n == 0: return "零"
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
    text = re.sub(r'([A-Z])', r' \1', text).strip()
    return text
```

使用 `--preprocess` 自动应用全部预处理。

### 推荐参数组合

```bash
# 最佳音质：预处理 + 归一化 + 微调语速音调
python3 "{baseDir}/scripts/tts.py" "长文本..." \
  --preprocess --normalize --speed 0.98 --pitch 1.02 -o output.wav

# 降噪 + 归一化
python3 "{baseDir}/scripts/tts.py" "你好" --denoise --normalize -o output.wav
```

## 🎧 ASR 优化

### 音频前置处理

```bash
# 统一 16k 采样率
ffmpeg -i input.mp3 -ar 16000 -ac 1 -sample_fmt s16 output.wav

# 自动预处理
python3 "{baseDir}/scripts/asr.py" audio.mp3 --preprocess -o transcript.txt
```

### 推荐参数

```bash
# 中文场景最优组合
python3 "{baseDir}/scripts/asr.py" audio.wav --preprocess --no-diarization --boost-cn -o transcript.txt

# 长音频
python3 "{baseDir}/scripts/asr.py" long.wav --chunk 30 --preprocess -o transcript.txt
```

## 🔧 工程化

### 全局单例模型加载

```python
import threading

_model_instance = None
_model_lock = threading.Lock()

def get_model():
    global _model_instance
    if _model_instance is None:
        with _model_lock:
            if _model_instance is None:
                _model_instance = load_model()
    return _model_instance
```

### 并发控制

```python
from concurrent.futures import ThreadPoolExecutor
import queue

MAX_CONCURRENT = 3
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)

def process_request(text, **kwargs):
    future = executor.submit(synthesize, text, **kwargs)
    return future.result(timeout=60)
```

### 音频缓存

```python
import hashlib, os

CACHE_DIR = "/tmp/mimo_tts_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_key(text, voice, style):
    return hashlib.md5(f"{text}:{voice}:{style}".encode()).hexdigest()

def get_cached_audio(text, voice, style):
    path = os.path.join(CACHE_DIR, f"{get_cache_key(text, voice, style)}.wav")
    return path if os.path.exists(path) else None
```

使用 `--cache` 启用。

## 🚀 高阶加速

### 模型剪枝（255M → ~150M）

```python
import torch
from transformers import AutoModel

model = AutoModel.from_pretrained("XiaomiMiMo/MiMo-V2.5-TTS")

def structured_prune(model, prune_ratio=0.4):
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Linear):
            torch.nn.utils.prune.l1_unstructured(module, name='weight', amount=prune_ratio)
    return model

pruned_model = structured_prune(model, prune_ratio=0.4)
pruned_model.save_pretrained("MiMo-V2.5-TTS-150M")
```

> ⚠️ 剪枝后需 fine-tune 恢复精度

### TensorRT（N 卡）

```bash
pip install tensorrt
# ONNX → TensorRT 转换，推理速度最快
```

### OpenVINO（Intel CPU/核显）

```bash
pip install openvino
mo --input_model model.onnx --output_dir openvino_model/
```

### FastAPI 封装

```python
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI(title="MiMo TTS ASR API")

@app.post("/tts")
async def tts_endpoint(text: str, voice: str = "mimo_default", speed: float = 1.0):
    audio = synthesize(text=text, voice=voice, speed=speed)
    output = "/tmp/output.wav"
    with open(output, "wb") as f:
        f.write(audio)
    return FileResponse(output, media_type="audio/wav")

@app.post("/asr")
async def asr_endpoint(audio: UploadFile = File(...), lang: str = "auto"):
    tmp = f"/tmp/{audio.filename}"
    with open(tmp, "wb") as f:
        f.write(await audio.read())
    return transcribe(tmp, lang=lang)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## ⚠️ 避坑

| 错误操作 | 后果 | 正确做法 |
|---------|------|---------|
| 加载完整版大权重 | 爆显存 | 用 255M 精简版 |
| 255M 开超高降噪 | 音质变差 | 降噪系数 ≤ 0.5 |
| 255M 开多人分离 | 效果差 + 耗性能 | `--no-diarization` |
| 一次性输入超长文本 | 卡顿吞字 | `--preprocess` 分句 |
| Windows pip 装环境 | 版本冲突 | 用 Conda |
