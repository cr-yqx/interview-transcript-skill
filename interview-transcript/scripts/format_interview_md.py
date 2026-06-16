from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys


DEFAULT_CORRECTIONS = {
    "Open AI": "OpenAI",
    "安斯罗皮克": "Anthropic",
    "DFc可": "DeepSeek",
    "planer": "Planner",
    "Panner": "Planner",
    "A型": "Agent",
    "A线": "Agent",
    "Azint": "Agent",
    "codco的和codex": "Claude Code 和 Codex",
    "Codeco的Codex": "Claude Code 和 Codex",
    "买二次": "Manus",
    "马拉斯": "Manus",
    "minus": "Manus",
}

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GLOSSARY_PATH = SKILL_DIR / "references" / "glossary.json"


def fmt_time(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def load_turns(path: Path | None) -> list[dict]:
    if not path:
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_corrections(path: Path, *, required: bool = True) -> dict[str, str]:
    if not path.exists():
        if required:
            raise SystemExit(f"Corrections file not found: {path}")
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Corrections file must be a JSON object: {path}")
    return {str(source): str(target) for source, target in data.items()}


def load_glossary_corrections(path: Path, *, required: bool = False) -> dict[str, str]:
    if not path.exists():
        if required:
            raise SystemExit(f"Glossary file not found: {path}")
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Glossary file must be a JSON object: {path}")
    corrections = data.get("corrections", {})
    if not isinstance(corrections, dict):
        raise SystemExit(f"Glossary corrections must be a JSON object: {path}")
    return {str(source): str(target) for source, target in corrections.items()}


def speaker_for(segment_id: int, turns: list[dict]) -> str:
    for turn in turns:
        if int(turn["start_id"]) <= segment_id <= int(turn["end_id"]):
            return str(turn["speaker"])
    return "说话人"


def clean_text(parts: list[str], corrections: dict[str, str]) -> str:
    text = " ".join(part.strip() for part in parts if part.strip())
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([，。！？、,.?])", r"\1", text)
    text = text.replace(" ,", "，")
    for source, target in sorted(corrections.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(source, target)
    return text.strip()


def add_grouped(grouped: list[dict], speaker: str, start: float, end: float, text: str) -> None:
    if grouped and grouped[-1]["speaker"] == speaker:
        grouped[-1]["end"] = end
        grouped[-1]["parts"].append(text)
        return
    grouped.append({"speaker": speaker, "start": start, "end": end, "parts": [text]})


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Format Whisper JSON as speaker-labeled interview Markdown.")
    parser.add_argument("json_path", help="Whisper JSON file")
    parser.add_argument("--out", help="Output Markdown path")
    parser.add_argument("--source", help="Original source file path")
    parser.add_argument("--turns", help="JSON file mapping segment ID ranges to speakers")
    parser.add_argument("--title", default="面试文字记录")
    parser.add_argument("--glossary", help="Optional extra glossary JSON with a corrections object")
    parser.add_argument("--no-default-glossary", action="store_true", help="Do not load references/glossary.json")
    parser.add_argument("--corrections", help="Optional JSON dictionary of ASR corrections")
    parser.add_argument("--print-segments", action="store_true", help="Print segment IDs, times, and text, then exit")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if args.print_segments:
        for segment in data.get("segments", []):
            print(
                f"{int(segment['id']):03d} "
                f"{fmt_time(float(segment['start']))}-{fmt_time(float(segment['end']))} "
                f"{str(segment.get('text', '')).strip()}"
            )
        return
    if not args.out:
        raise SystemExit("--out is required unless --print-segments is used")

    turns = load_turns(Path(args.turns) if args.turns else None)
    corrections = dict(DEFAULT_CORRECTIONS)
    if not args.no_default_glossary:
        corrections.update(load_glossary_corrections(DEFAULT_GLOSSARY_PATH, required=False))
    if args.glossary:
        corrections.update(load_glossary_corrections(Path(args.glossary), required=True))
    if args.corrections:
        corrections.update(load_corrections(Path(args.corrections), required=True))

    grouped: list[dict] = []
    for segment in data.get("segments", []):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        segment_id = int(segment["id"])
        speaker = speaker_for(segment_id, turns) if turns else "说话人"
        add_grouped(grouped, speaker, float(segment["start"]), float(segment["end"]), text)

    duration = max((float(s.get("end", 0)) for s in data.get("segments", [])), default=0)
    lines = [f"# {args.title}", ""]
    if args.source:
        lines.append(f"- 来源文件：`{args.source}`")
    lines.extend(
        [
            f"- 音频时长：约 {fmt_time(duration)}",
            "- 转写方式：本地 Whisper 自动转写",
            "- 说明：说话人标签可能由时间段推断；专名、技术词和个别口误建议结合原音频复核。",
            "",
            "## 逐轮记录",
            "",
        ]
    )

    for item in grouped:
        text = clean_text(item["parts"], corrections)
        if not text:
            continue
        lines.append(f"### {fmt_time(item['start'])}-{fmt_time(item['end'])} {item['speaker']}")
        lines.append("")
        lines.append(text)
        lines.append("")

    Path(args.out).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
