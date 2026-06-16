from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


DEFAULT_FFMPEG_DIRS = [
    Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\FloXpress\bin"),
    Path(r"C:\Program Files\BlueStacks_nxt"),
]


def add_paths(package_dir: Path | None, ffmpeg_dir: Path | None) -> None:
    if package_dir:
        sys.path.insert(0, str(package_dir))
    dirs = [ffmpeg_dir] if ffmpeg_dir else DEFAULT_FFMPEG_DIRS
    for path in dirs:
        if path and path.exists():
            os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")


def write_outputs(result: dict, out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}.whisper.json"
    txt_path = out_dir / f"{stem}.whisper.txt"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(result.get("text", "").strip() + "\n", encoding="utf-8-sig")
    print(f"Wrote {json_path}")
    print(f"Wrote {txt_path}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Run local Whisper transcription for interviews.")
    parser.add_argument("audio", help="Audio or video file to transcribe")
    parser.add_argument("--out-dir", required=True, help="Directory for JSON/TXT outputs")
    parser.add_argument("--model", default="small", help="Whisper model name")
    parser.add_argument("--language", default="zh", help="Language hint")
    parser.add_argument("--package-dir", help="Project-local Python package directory containing whisper")
    parser.add_argument("--model-dir", help="Directory for Whisper model weights")
    parser.add_argument("--ffmpeg-dir", help="Directory containing ffmpeg.exe")
    parser.add_argument("--stem", help="Output file stem")
    parser.add_argument("--prompt", default="以下是普通话面试录音转写，请使用简体中文，保留产品、实习、项目、技术名词，按原话记录。")
    args = parser.parse_args()

    audio = Path(args.audio)
    if not audio.exists():
        raise SystemExit(f"Audio/video file not found: {audio}")

    package_dir = Path(args.package_dir) if args.package_dir else None
    ffmpeg_dir = Path(args.ffmpeg_dir) if args.ffmpeg_dir else None
    add_paths(package_dir, ffmpeg_dir)

    import torch
    import whisper

    model_dir = Path(args.model_dir) if args.model_dir else Path(args.out_dir) / "_whisper_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model(args.model, download_root=str(model_dir))
    result = model.transcribe(
        str(audio),
        language=args.language,
        task="transcribe",
        fp16=bool(torch.cuda.is_available()),
        temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        condition_on_previous_text=False,
        hallucination_silence_threshold=2.0,
        verbose=True,
        initial_prompt=args.prompt,
    )

    stem = args.stem or audio.stem
    write_outputs(result, Path(args.out_dir), stem)


if __name__ == "__main__":
    main()
