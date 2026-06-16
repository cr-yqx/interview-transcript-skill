---
name: interview-transcript
description: Transcribe interview audio or video files into Markdown with timestamps and inferred speaker turns. Use when Codex needs to extract full interview dialogue from OBS recordings, MP4/M4A/WAV/audio files, meeting recordings, or candidate interviews, especially when the user asks for "面试文字记录", "双方记录", "整理成 md", speaker-labeled transcripts, or reusable local Whisper transcription workflows.
---

# Interview Transcript

## Overview

Create a complete interview transcript from a local audio/video file and save it as Markdown. Prefer this skill for Chinese interview recordings, OBS MP4 files, and large WAV files exported from OBS or screen recordings.

## Workflow

1. Locate the real source file. If the user-provided path is missing, search nearby folders before asking.
2. Create an output folder under `output/transcribe/<job-id>/` in the current workspace.
3. Inspect the source duration and shape before transcription:
   - Use `ffprobe` when available.
   - If `ffprobe` is unavailable for WAV, use Python `wave` to read channels, sample rate, frames, and duration.
4. Extract or normalize compact mono audio with ffmpeg:
   - For video, extract audio first.
   - For large WAV files, transcode to 16 kHz mono AAC/M4A before Whisper; this avoids feeding hundreds of MB of PCM directly to the model.
   - Prefer AAC/M4A when MP3 encoders are unavailable.
   - Keep the extracted audio under API/model-friendly size where possible.
5. Try the existing `transcribe` skill/OpenAI transcription path only if it is already available and appropriate.
6. If remote transcription is blocked, unavailable, or not desired, use local Whisper through `scripts/run_whisper_transcribe.py`.
7. Inspect the Whisper JSON for hallucination, repeated filler, incorrect tail segments, or speaker-turn boundary issues.
8. Generate Markdown with `scripts/format_interview_md.py`; pass manual segment speaker ranges when speaker diarization is unavailable. The formatter loads `references/glossary.json` first, then overlays the current job's `corrections.json`.
9. Create `<job-dir>/glossary_candidates.json` after reviewing the transcript:
   - `public_terms`: reusable non-sensitive terms from internet, large-model, Agent, product, and robotics interviews.
   - `local_only_terms`: company names, people names, project names, role details, business parties, URLs, tokens, local paths, and interview-specific content.
10. Final-check the Markdown with `Get-Content` and mention any limitations in the final response.
11. If the user confirms skill learning, merge only reviewed `public_terms` into `references/glossary.json`, then sync and push the public skill repo.

## WAV Prep

For large WAV input, make a job folder and normalize to compact mono M4A before running Whisper:

```powershell
$jobDir = "<workspace>\output\transcribe\<job-id>"
New-Item -ItemType Directory -Force -Path $jobDir | Out-Null

& "<ffmpeg.exe>" -y -hide_banner `
  -i "<source.wav>" `
  -vn -ac 1 -ar 16000 -c:a aac -b:a 64k `
  "$jobDir\interview_audio.m4a"
```

If `ffprobe` is unavailable, inspect WAV duration with Python:

```powershell
& "<python.exe>" -c "import wave; p=r'<source.wav>'; w=wave.open(p,'rb'); print({'channels':w.getnchannels(),'sample_rate':w.getframerate(),'frames':w.getnframes(),'duration':w.getnframes()/w.getframerate()}); w.close()"
```

## Local Whisper Command

Use the bundled script when local Whisper is needed:

```powershell
$env:PYTHONUTF8 = "1"
& "<python.exe>" "<skill-dir>\scripts\run_whisper_transcribe.py" `
  "<audio-or-video-file>" `
  --out-dir "<workspace>\output\transcribe\<job-id>" `
  --model small `
  --language zh
```

Notes:
- Use a Python environment with `torch` installed when possible; the user's `C:\Users\Administrator\anaconda3\envs\ai_study\python.exe` has worked before.
- Before a long transcription, smoke-test the runtime:
  `python -c "import sys; sys.path.insert(0, r'<package-dir>'); import whisper; print(getattr(whisper,'__file__',None), hasattr(whisper,'load_model'))"`
- If `whisper` imports as an empty namespace package or `load_model` is missing, reinstall into a fresh project-local target directory.
- Add `openai-whisper`, `tiktoken`, `more-itertools`, `numba`, and `llvmlite` to a project-local target directory if missing.
- When installing packages, set `TEMP`, `TMP`, and `PIP_CACHE_DIR` inside the workspace. Avoid elevated installs into the target directory when possible; they can leave package directories unreadable to the normal session.
- Prefer `small` as the reliable default. Larger models may improve quality but can download slowly or leave partial weights.
- The script sets `condition_on_previous_text=False` and `hallucination_silence_threshold=2.0` to reduce repeated tail hallucinations.

Project-local install pattern:

```powershell
$env:PYTHONUTF8 = "1"
$env:TEMP = "<workspace>\output\pip_tmp"
$env:TMP = "<workspace>\output\pip_tmp"
$env:PIP_CACHE_DIR = "<workspace>\output\pip_cache"
New-Item -ItemType Directory -Force -Path $env:TEMP, $env:PIP_CACHE_DIR | Out-Null

& "<python.exe>" -m pip install --no-cache-dir `
  --target "<workspace>\output\whisper_runtime_sandbox" `
  openai-whisper --no-deps tiktoken more-itertools numba llvmlite
```

## Markdown Formatting

If diarized JSON is unavailable, infer speaker turns from content and timestamps. For reliable results:

- Print Whisper segment IDs, times, and text with `--print-segments`.
- Save that output as `segments.txt` for manual speaker-range review.
- If the first segment repeats the transcription prompt, create a cleaned JSON that removes only that hallucinated segment before formatting.
- Map contiguous segment ID ranges to `面试官` or `候选人`.
- Use special splits only for segments that clearly contain both speakers.
- Apply only high-confidence correction rules for ASR errors, especially names like `Agent`, `Planner`, `OpenAI`, `Anthropic`, `DeepSeek`, `Manus`, `Claude Code`, and `Codex`.
- Avoid broad substring corrections that can corrupt already-correct terms; for example, do not replace `Agen` with `Agent` because it turns `Agent` into `Agentt`.
- Keep job-specific fixes in `<job-dir>/corrections.json`; keep reusable, non-sensitive fixes in `references/glossary.json`.

Run:

```powershell
$env:PYTHONUTF8 = "1"
& "<python.exe>" "<skill-dir>\scripts\format_interview_md.py" "<whisper-json>" --print-segments

& "<python.exe>" "<skill-dir>\scripts\format_interview_md.py" `
  "<whisper-json>" `
  --out "<job-dir>\<job-id>_面试文字记录.md" `
  --source "<original-video-path>" `
  --turns "<job-dir>\speaker_turns.json" `
  --corrections "<job-dir>\corrections.json"
```

The `speaker_turns.json` file should be a list like:

```json
[
  {"start_id": 0, "end_id": 0, "speaker": "面试官"},
  {"start_id": 1, "end_id": 10, "speaker": "候选人"}
]
```

## Glossary Learning

Maintain `references/glossary.json` as a public, reusable, non-sensitive vocabulary and ASR correction file. It is safe for GitHub only when it contains generic professional terms and common transcription mistakes.

After each transcript, write a local candidate file:

```json
{
  "public_terms": ["RAG", "Embedding", "BERT", "Agent", "vibe coding", "PRD"],
  "local_only_terms": ["公司名", "项目名", "面试岗位", "人名", "具体业务方"]
}
```

Rules:
- Put internet, large-model, Agent, product, robotics, and general engineering terms in `public_terms`.
- Put company names, interview roles, project names, business names, personal identifiers, URLs, account/token names or values, local machine paths, and transcript-specific facts in `local_only_terms`.
- Do not auto-promote all ASR corrections. Add correction rules to the public glossary only when they are high-confidence, reusable, and non-sensitive.
- Do not store audio, video, Markdown transcripts, Whisper JSON/TXT, local package paths, model weights, GitHub tokens, API keys, or machine-specific paths in the skill or public repo.

Merge reviewed public terms:

```powershell
$env:PYTHONUTF8 = "1"
& "<python.exe>" "<skill-dir>\scripts\update_glossary.py" `
  "<job-dir>\glossary_candidates.json"
```

Manually add one safe public ASR correction when needed:

```powershell
& "<python.exe>" "<skill-dir>\scripts\update_glossary.py" `
  "<job-dir>\glossary_candidates.json" `
  --correction "Webcoding=vibe coding"
```

Sync the local skill to the public GitHub repo after review:

```powershell
& "<skill-dir>\scripts\sync_skill_repo.ps1" `
  -RepoRoot "<repo-root>" `
  -GitPath "<git.exe>" `
  -CommitMessage "Update glossary for interview transcript skill" `
  -Push
```

## Validation

Before finishing:

- Confirm the Markdown opens as readable UTF-8 with BOM in PowerShell.
- Check the first 30 lines, the final 30 lines, and several speaker changes.
- Count `### ` headings to ensure turns were generated.
- Search for known artifacts such as the prompt text (`请使用简体中文`) and corrupted corrections (`Agentt`).
- Tell the user if labels are inferred rather than diarized and if terminology may need audio review.
