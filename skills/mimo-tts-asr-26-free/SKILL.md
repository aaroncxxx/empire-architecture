# MiMo TTS & ASR v2.99.92 Free For Now

语音合成（TTS）与语音识别（ASR）Skill。三款 TTS 模型限时免费，ASR 云端预留中。

> **关于作者** — 十五年老米粉，用龙虾编程，撸起袖子就是干。
>
> **ClawHub Skill vs 官方 MiMo V2.5 TTS 差异分析**
>
> 官方提供的是"模型能力"，本 Skill 提供的是"工程化产品"——防限流、长文本分句、edge-tts 兜底、缓存、重试，这些生产环境必须但官方不提供的东西，全在这了。官方是引擎，本 Skill 是整车。
>
> | 维度 | 本 Skill | 官方 |
> |------|---------|------|
> | 三合一封装 | 一个脚本统一调用 3 款 TTS 模型 | 只给 API，不给封装脚本 |
> | edge-tts 兜底 | 无 Key 自动降级到免费 TTS | 无降级方案 |
> | 防限流 | 随机延迟 + 并发控制 | 无客户端限流策略 |
> | 长文本分句 | 120 字/段自动切分 | 不处理长文本 |
> | 音频缓存 | 相同文本秒返，零消耗 | 无缓存 |
> | 异常重试 | 502/503/timeout 自动重试 | 不处理 |
> | 文本预处理 | 数字/符号/格式自动规范化 | 不处理 |
> | ASR 封装 | asr.py 封装（需 GPU 或等云端开放） | 只开源模型，不给脚本 |
> | 联合工作流 | TTS + ASR 串联示例 | 无工作流文档 |
> | 开源方案指南 | edge-tts/ChatTTS/GPT-SoVITS 等推荐 | 无 |
> | 批量合成 | `--file` 逐行读取批量处理 | 无 |
> | 格式自动检测 | 根据 `-o` 后缀推断格式 | 需手动指定 |
> | 默认预处理 | 数字/符号自动规范化（默认开启） | 无 |
> | 智能音色推荐 | `--recommend-voice` 根据情感/语言自动选音色 | 无 |
> | 质量自检 | 合成后自动检测空文件/静音/过短 | 无 |
> | 目录监听 | `--watch` 自动合成新增 .txt 文件 | 无 |

## 系统依赖

- **ffmpeg/ffprobe**：音频预处理、分片、格式转换必需
- **python3**：运行脚本

```bash
apt install ffmpeg  # Debian/Ubuntu
brew install ffmpeg  # macOS
```

## 配置

```bash
export MIMO_API_KEY="your-api-key"
```

或通过 OpenClaw 配置：
```bash
openclaw config set skills.entries.mimo-tts-asr.apiKey "your-key"
```

申请 Key：[platform.xiaomimimo.com](https://platform.xiaomimimo.com)（当前限时免费）

> 🎧 **在线体验**：[MiMo Studio](https://aistudio.xiaomimimo.com/#/c) 可快速试听各模型效果，无需配置。

> 💡 **无 Key 也能用**：不设 `MIMO_API_KEY` 时自动走 edge-tts 免费通道（仅支持预置音色模式）

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MIMO_API_KEY` | — | MiMo TTS API Key（必填，或走 edge-tts 兜底） |
| `MIMO_ASR_KEY` | — | ASR API Key（可与 TTS 相同） |
| `MIMO_API_ENDPOINT` | `https://api.xiaomimimo.com/v1` | API 端点（可自定义） |
| `MIMO_TTS_MODEL` | `mimo-v2-audio-tts` | 默认 TTS 模型名 |
| `MIMO_VOICE_SAMPLE` | — | 默认声音克隆参考音频路径 |
| `USE_CLOUD_TTS` | `1` | 设为 `0` 切换到 edge-tts 兜底 |

## TTS — 语音合成

### 基础用法

```bash
python3 "{baseDir}/scripts/tts.py" "要合成的文本" -o output.wav
```

### 三款模型

| 模型 | 用途 | 关键参数 |
|------|------|---------|
| `tts`（默认） | 内置音色 + 情感/语速控制 | `-v` 音色, `-s` 风格 |
| `voice-design` | 自然语言描述生成新音色 | `--voice-desc` |
| `voice-clone` | 参考音频克隆音色 | `--ref-audio` |

### 预置音色

| 音色 | 语言 | 性别 | 风格 |
|------|------|------|------|
| 冰糖 | 中文 | 女 | 活泼少女，清脆甜美 |
| 茉莉 | 中文 | 女 | 知性女声，温柔稳重 |
| 苏打 | 中文 | 男 | 阳光少年，活力朝气 |
| 白桦 | 中文 | 男 | 成熟男声，沉稳大气 |
| Mia | English | Female | Lively girl |
| Chloe | English | Female | Witty Grace |
| Milo | English | Male | Sunny boy |
| Dean | English | Male | Steady Gentle |

> 💡 不设 `MIMO_API_KEY` 时自动走 **edge-tts** 免费通道（音色自动匹配）

### TTS 参数速查

### 行内音频标签

在文本中插入精细控制：
`(停顿) (叹气) (笑声) (清嗓子) (耳语) (紧张) (小声) (语速加快) (深呼吸) (沉默片刻)`

> 💡 **多标签组合**：`开心 变快` 放在文本开头设置整体风格。支持任意自然语言风格短语，无固定值限制。

### 导演剧本级结构化输入

对于有声剧、游戏角色、角色化对话等高一致性场景，支持分层描述：

```bash
python3 "{baseDir}/scripts/tts.py" "
【人物】林黛玉，柔弱敏感，语速偏慢
【场景】葬花，暮春时节，落花满地
【指导】声音带哽咽感，气息不稳，尾音渐弱
花谢花飞花满天，红消香断有谁怜？
" -o lin_daiyu.wav
```

模型会将人物、场景、指导三层独立理解，保持角色音色贯穿，同时每句话的表演单独控制。

### 文本理解能力

无需任何 prompt 或标签——纯文本也能自动表现出韵律与情感：

- **标点停顿**：句号、逗号、省略号自动对应自然停顿
- **情感弧线**：从平静到激烈的情感转折自动捕捉
- **说话人身份**：字里行间的年龄、气质、角色类型自动落入声音

```bash
# 零 prompt，模型自动理解文本情感
python3 "{baseDir}/scripts/tts.py" "他沉默了很久，终于开口：算了，就这样吧。" -o auto_emotion.wav
```

### 唱歌模式

传入歌词即可合成歌声：

```bash
# 直接传歌词
python3 "{baseDir}/scripts/tts.py" "两只老虎，两只老虎，跑得快" -s "唱歌" -o song.wav

# 歌名字典查找（需 sing0301_dict.json）
python3 "{baseDir}/scripts/tts.py" "两只老虎" -s "唱歌" -o song.wav

# 英文歌词
python3 "{baseDir}/scripts/tts.py" "Yesterday, all my troubles seemed so far away" -s "唱歌" -o song_en.wav
```

### 文本规范化指南

合成前建议对输入文本做预处理，确保数字、符号、格式渲染为自然口语：

**数字**
| 输入 | 口语化 |
|------|--------|
| `3.14` | 三点一四 |
| `1/3` | 三分之一 |
| `14:30` | 下午两点半 |
| `95%` | 百分之九十五 |
| `2024`（年份） | 二零二四年 |

**符号**
| 符号 | 口语化 |
|------|--------|
| `+` `-` `×` `÷` | 加 减 乘以 除以 |
| `=` `>` `<` | 等于 大于 小于 |
| `~` | 大约 |
| `...` `…` | 等等 |

**格式清理**
- 去掉 markdown 标记（`**bold**`、`# heading`、`` `code` ``）
- 编号列表转口语：「有三点，第一……第二……第三……」
- 表格转描述句

> 💡 开启 `--preprocess` 参数可自动完成上述大部分预处理。

> **📝 v3.0 变更**：预处理现在默认开启，无需手动加 `--preprocess`。如需关闭，使用 `--no-preprocess`。

### 核心示例

```bash
# 基础
python3 "{baseDir}/scripts/tts.py" "你好，今天天气真好" -o hello.wav

# 方言
python3 "{baseDir}/scripts/tts.py" "哎呀妈呀，这天儿也忒冷了吧" -s "东北话" -o dongbei.wav

# 情感 + 语速
python3 "{baseDir}/scripts/tts.py" "明天就是周五了！" -s "开心 变快" -o happy.wav

# 男声 / 童声 / 粤语
python3 "{baseDir}/scripts/tts.py" "大家好" -v 苏打 -o male.wav

# VoiceDesign — 生成新音色
python3 "{baseDir}/scripts/tts.py" "欢迎" -m voice-design \
  --voice-desc "元气少女，声线清脆，语尾上扬" -o genki.wav

# VoiceClone — 克隆音色
python3 "{baseDir}/scripts/tts.py" "克隆后的声音" -m voice-clone \
  --ref-audio reference.wav -o cloned.wav

# 推荐组合：预处理 + 归一化 + 微调
python3 "{baseDir}/scripts/tts.py" "长文本..." --normalize -o output.wav
```

### 批量合成

从文件逐行读取文本，批量生成音频：

```bash
# 准备文本文件（每行一段）
cat > lines.txt << 'EOF'
欢迎收听今天的节目
接下来为您播报天气预报
感谢您的收听，下次再见
EOF

# 批量合成
python3 "{baseDir}/scripts/tts.py" --file lines.txt -o output.wav

# 输出：output_001.wav, output_002.wav, output_003.wav
```

### 智能音色推荐

根据文本内容自动选择最佳音色（情感检测 + 语言判断）：

```bash
python3 "{baseDir}/scripts/tts.py" "恭喜你获得了一等奖！" --recommend-voice -o output.wav
# [智能推荐] 音色: 冰糖（检测到开心情感）

python3 "{baseDir}/scripts/tts.py" "Important meeting tomorrow" --recommend-voice -o output.wav
# [智能推荐] 音色: Mia（检测到英文内容）
```

**推荐逻辑：**
| 情感/语言 | 中文推荐 | 英文推荐 |
|-----------|---------|---------|
| 开心/欢快 | 冰糖 | Mia |
| 悲伤/温柔 | 茉莉 | Chloe |
| 生气/激动 | 苏打 | Milo |
| 严肃/正式 | 白桦 | Dean |
| 默认 | 冰糖 | Mia |

### 格式自动检测

根据 `-o` 输出路径后缀自动推断格式，无需手动指定 `-f`：

```bash
python3 "{baseDir}/scripts/tts.py" "你好" -o output.wav    # → WAV
python3 "{baseDir}/scripts/tts.py" "你好" -o output.mp3    # → MP3
python3 "{baseDir}/scripts/tts.py" "你好" -o output.ogg    # → OGG
```

### 目录监听模式

监听目录，自动合成新增的 `.txt` 文件：

```bash
# 启动监听（Ctrl+C 退出）
python3 "{baseDir}/scripts/tts.py" --watch /path/to/watch

# 往目录里放 .txt 文件，自动生成同名音频
echo "新的一段文本" > /path/to/watch/news.txt
# → 自动生成 /path/to/watch/news.wav
```

### 质量自检

合成后自动检测输出质量：
- ❌ 文件不存在 → 报错
- ❌ 文件为空 → 报错
- ⚠️ 文件过小 (<1KB) → 警告（可能静音）
- ⚠️ WAV 头异常 → 警告

## ASR — 语音识别（云端预留）

> ⚠️ ASR 云端 API 暂未开放，以下为预留文档。本地部署需 GPU（CUDA），详见 [GitHub](https://github.com/XiaomiMiMo/MiMo-V2.5-ASR)。

### 基础用法

```bash
python3 "{baseDir}/scripts/asr.py" audio.wav
```

### 参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `-o` | stdout | 输出路径 |
| `--lang` | auto | 语言：auto / zh / en / ja / ko |
| `--format` | text | 输出：text / json / srt |
| `--preprocess` | 关 | 音频预处理（采样率/静音裁剪） |
| `--chunk` | 0 | 长音频分片秒数（0=不分片） |
| `--max-retries` | 3 | 最大重试次数 |

### 核心示例

```bash
# 基础转录
python3 "{baseDir}/scripts/asr.py" recording.wav

# 保存到文件
python3 "{baseDir}/scripts/asr.py" meeting.mp3 -o meeting.txt

# SRT 字幕
python3 "{baseDir}/scripts/asr.py" video_audio.wav --format srt -o subtitles.srt
```

## TTS + ASR 联合工作流（云端预留）

```bash
# 1. 识别（需本地 GPU 或云端 API 开放后使用）
python3 "{baseDir}/scripts/asr.py" input.wav -o transcript.txt

# 2. 修改后用不同音色重新合成
python3 "{baseDir}/scripts/tts.py" "$(cat transcript.txt)" -v 苏打 -o output.wav
```

## 交付格式

- **TTS**：`MEDIA:output.wav`（或指定的 `-o` 路径）
- **ASR**：直接回复转录文本，或回复 `-o` 指定的文件路径

### 输出格式保证

| 属性 | 值 |
|------|-----|
| 格式 | WAV (RIFF) / MP3 / OGG（通过 `-f` 切换） |
| 采样率 | 24,000 Hz |
| 位深 | 16-bit PCM |
| 声道 | Mono |

- API 返回 PCM 时自动补 RIFF WAV 头
- 输出文件写入失败时返回非零退出码 + 错误信息
- 支持 `--denoise` 后置降噪、`--normalize` 音量归一化
- 支持 `--cache` 相同文本秒返（缓存持久化到 `{baseDir}/cache`）

## 故障排查

| 错误 | 原因 | 解决 |
|------|------|------|
| 401 Invalid API Key | Key 未配置或格式错误 | 确认已配置 `MIMO_API_KEY`，检查是否为平台申请的正确 Key |
| 429 Too Many Requests | 触发限流 | 等几秒重试（脚本自动重试，最大 3 次） |
| 502/503 Bad Gateway | 服务端临时异常 | 脚本自动重试，连续失败则检查服务状态 |
| Timeout | 网络超时 | 检查网络连接，脚本自动重试 |
| 文件不存在 | 路径错误 | 检查音频文件路径，确认父目录存在 |
| ffmpeg 未找到 | 缺系统依赖 | `apt install ffmpeg` 或 `brew install ffmpeg` |
| edge-tts 未安装 | 兜底方案缺失 | `pip install edge-tts` |
| 输出文件为空 | API 返回异常 | 检查 Key 余额、文本长度，查看 stderr 原始响应 |

## 进阶优化

推理性能优化（GPU/CPU）、模型剪枝、TensorRT/OpenVINO 加速、FastAPI 封装等高级用法，详见 `docs/advanced.md`。

## 性能基准

典型延迟数据（仅供参考，实际受网络和文本长度影响）：

| 场景 | 文本长度 | 延迟 | 说明 |
|------|---------|------|------|
| 短句 | <20 字 | ~1-2s | 最常见场景 |
| 中等段落 | 20-80 字 | ~2-4s | 正常语速 |
| 长文本 | 80-200 字 | ~4-8s | 自动分句 |
| 超长文本 | >200 字 | ~8-15s | 多段拼接 |
| edge-tts 兜底 | 任意 | ~1-3s | 不经过 MiMo API |
| 缓存命中 | 任意 | <0.1s | 零消耗 |

> 💡 首次合成较慢（冷启动），后续相同文本走缓存秒返。

## 费用说明

| 项目 | 当前 | 正式价格（参考） |
|------|------|----------------|
| MiMo TTS | **限时免费** | 未公布，预计按字符计费 |
| MiMo VoiceDesign | **限时免费** | 未公布 |
| MiMo VoiceClone | **限时免费** | 未公布 |
| edge-tts | **永久免费** | — |

**Token 消耗估算（MiMo API）：**
- 短句（20 字）≈ 20-30 tokens
- 中等段落（100 字）≈ 100-150 tokens
- 长文本（500 字）≈ 500-750 tokens

> ⚠️ 限时免费期间无消耗，正式计费后建议开启 `--cache` 减少重复合成。

## 质量对比

| 维度 | MiMo TTS v2.5 | edge-tts | ChatTTS | GPT-SoVITS |
|------|---------------|----------|---------|------------|
| 音质 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 中文支持 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 情感控制 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 声音克隆 | ⭐⭐⭐⭐⭐ | ❌ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 延迟 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 部署难度 | 云端免费 | 云端免费 | 需 GPU | 需 GPU |
| 适合场景 | 通用/专业 | 简单播报 | 对话/闲聊 | 专业配音 |

## 开源免费 TTS 备选方案

以下为可替代或补充 MiMo TTS 的开源方案，按是否需要 GPU / 免费 API 分类：

### 免费云端（无需 GPU、无需 API Key）

| 项目 | ⭐ | 说明 | 安装 |
|------|-----|------|------|
| **edge-tts** | 10.7k | 微软 Edge 在线 TTS，中文音色丰富，完全免费 | `pip install edge-tts` |

### 需自建部署（需 GPU）

| 项目 | ⭐ | 说明 |
|------|-----|------|
| **ChatTTS** | 39.2k | 日常对话语音生成，效果自然 |
| **CosyVoice** | 20.7k | 阿里多语言大模型，支持中英日韩 |
| **fish-speech** | 29.9k | SOTA 开源 TTS，音质极高 |

### GitHub TTS 项目星数 Top 5

| # | 项目 | ⭐ | 说明 |
|---|------|-----|------|
| 1 | **Real-Time-Voice-Cloning** | 59.6k | 5秒实时语音克隆 |
| 2 | **GPT-SoVITS** | 56.9k | 1分钟数据训练 TTS（少样本克隆） |
| 3 | **coqui-ai/TTS** | 45.2k | 生产级深度学习 TTS 工具包 |
| 4 | **ChatTTS** | 39.2k | 日常对话语音生成 |
| 5 | **MockingBird** | 36.9k | 5秒实时语音克隆 |

> 💡 **推荐组合**：MiMo TTS（云端免费）+ edge-tts（备用免费）+ GPT-SoVITS（自建克隆）

## 版本历史

### v2.99.92 (2026-04-24)
- 🚀 **批量合成**：`--file` 逐行读取文本文件批量处理
- 🧠 **智能音色推荐**：`--recommend-voice` 根据情感/语言自动选音色
- 📐 **格式自动检测**：根据 `-o` 后缀推断 wav/mp3/ogg
- ⚡ **默认预处理**：数字/符号自动规范化（`--no-preprocess` 关闭）
- 🔍 **质量自检**：合成后自动检测空文件/静音/过短
- 👀 **目录监听**：`--watch` 自动合成新增 .txt 文件
- 📊 新增性能基准、费用说明、质量对比表
- 🎤 `--list-voices` 增加推荐场景信息

### v2.99.3 (2026-04-24)
- ✨ 新增导演剧本级结构化输入文档与示例
- ✨ 新增文本理解能力说明（零 prompt 自动情感表达）
- 🔗 新增 MiMo Studio 在线体验链接

### v2.99.2 (2026-04-24)
- ✨ 新增声音克隆详细文档与示例
- ✨ 新增唱歌模式文档（歌词直传 + 歌名字典）
- ✨ 新增完整文本规范化指南（数字/符号/格式）
- ✨ 新增环境变量覆盖表（6 项可配置）
- ✨ 新增输出格式保证说明（格式/采样率/位深/声道）
- 📋 故障排查扩展至 8 项（新增 502/503/Timeout/edge-tts/空文件）

### v2.99 (2026-04-24)
- 🛡️ 防限流：随机延迟 0.3~0.6s + 最大并发限制 (MAX_CONCURRENT=2)
- 📝 长文本自动分句分段合成（120字/段，按标点切分）
- 🔁 异常捕获：502/503/timeout 自动重试，不闪退
- 🔒 隐私：不打印 Key，临时文件自动清理
- ⚡ 开关：USE_CLOUD_TTS 一键切本地/edge-tts
- 🎤 音色表增加风格描述
- 📂 缓存目录改为 `{baseDir}/cache`（持久化）
- ⚠️ ffmpeg 缺失时给出明确提示
- 🔧 scripts 添加执行权限

### v2.95 (2026-04-24)
- 📝 标题更新为 MiMo TTS & ASR v2.95 Free For Now
- 🔧 修复默认音色（`mimo_default` → `冰糖`）
- ⚡ `--speed` / `--pitch` 标注为预留参数
- ☁️ ASR 部分标注云端预留
- 📋 示例修正为实际可用音色

### v2.92 (2026-04-24)
- ✅ 新增 `scripts/tts.py` — 三合一 TTS 脚本（预置音色/音色设计/音色克隆）
- ✅ 新增 `scripts/asr.py` — ASR 语音识别脚本（需本地 GPU）
- 🔗 API 对接 `https://api.xiaomimimo.com/v1`

### v2.9 (2026-04-24)
- 📐 SKILL.md 精简重构，聚焦用法，进阶内容拆至 docs/
- 🔧 修复 `--preprocess` 参数语义矛盾（改为显式开启）
- 📋 参数表统一格式，示例精简到核心场景

### v2.81 (2026-04-24)
- 📦 声明系统依赖 ffmpeg/ffprobe
- 🔑 明确 API Key 要求

### v2.8 (2026-04-24)
- 🚀 进阶优化：剪枝 / TensorRT / OpenVINO / FastAPI
- ⚠️ 避坑要点
