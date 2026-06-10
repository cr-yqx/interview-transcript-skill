# Interview Transcript Codex Skill

This repository contains a Codex skill for transcribing interview audio or video files into speaker-labeled Markdown with timestamps.

## What It Does

- Handles local interview recordings, including large WAV files exported from OBS or screen recordings.
- Normalizes large WAV/video inputs to compact mono audio before transcription.
- Uses local Whisper when remote transcription is unavailable or not desired.
- Helps inspect Whisper segments, infer interview speaker turns, and produce Markdown.

## Install

Copy the skill folder into your Codex skills directory:

```powershell
Copy-Item -Recurse ".\interview-transcript" "$env:USERPROFILE\.codex\skills\"
```

Then use it in Codex:

```text
$interview-transcript transcribe this interview audio into Markdown
```

## Privacy

Do not commit source audio, generated transcripts, Whisper JSON/TXT output, model weights, or local runtime caches. The `.gitignore` file excludes common local artifacts.

## Requirements

- Python 3.10+ recommended
- `ffmpeg` available in `PATH`, or pass `--ffmpeg-dir` to the bundled script
- Local Whisper dependencies when using the local path:
  - `openai-whisper`
  - `tiktoken`
  - `more-itertools`
  - `numba`
  - `llvmlite`
  - `torch`
