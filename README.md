# Interview Transcript Codex Skill

这是一个用于面试录音/录像转写的 Codex Skill，可以把本地音频或视频整理成带时间戳、带说话人标签的 Markdown 文稿。

## 功能

- 支持本地面试录音、OBS 录制文件、MP4/M4A/WAV 等常见音视频格式。
- 针对 OBS 或屏幕录制导出的大体积 WAV，先转成 16 kHz 单声道 M4A，再交给 Whisper 转写。
- 在远程转写不可用或不希望上传音频时，使用本地 Whisper。
- 输出 Whisper JSON/TXT，并辅助生成按轮次合并的 Markdown。
- 支持人工维护 `speaker_turns.json`，把 Whisper 小段合并成“面试官/候选人”的对话轮次。

## 安装

把 `interview-transcript` 目录复制到本机 Codex skills 目录：

```powershell
Copy-Item -Recurse ".\interview-transcript" "$env:USERPROFILE\.codex\skills\"
```

之后在 Codex 中使用：

```text
$interview-transcript 把这个面试音频转成 Markdown 文字记录
```

## 依赖

- Python 3.10+
- `ffmpeg`，需要在 `PATH` 中，或者运行脚本时传入 `--ffmpeg-dir`
- 本地 Whisper 转写依赖：
  - `openai-whisper`
  - `tiktoken`
  - `more-itertools`
  - `numba`
  - `llvmlite`
  - `torch`

## 隐私说明

请不要把以下内容提交到仓库：

- 原始音频或视频
- 生成的转写 Markdown
- Whisper JSON/TXT 输出
- Whisper 模型权重
- 本地 Python 依赖目录、pip 缓存、临时文件

仓库里的 `.gitignore` 已经排除了常见的本地转写产物和缓存目录。

## 目录结构

```text
interview-transcript/
├─ SKILL.md
├─ agents/
│  └─ openai.yaml
└─ scripts/
   ├─ run_whisper_transcribe.py
   └─ format_interview_md.py
```

`SKILL.md` 是 Codex 实际读取的技能说明；`scripts/` 里是可复用的本地 Whisper 转写和 Markdown 格式化脚本。
