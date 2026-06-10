from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys


DEFAULT_CORRECTIONS = {
    "Open AI": "OpenAI",
    "planer": "Planner",
    "Panner": "Planner",
    "Azint": "Agent",
    "Deepseek": "DeepSeek",
    "ClaudeCode": "Claude Code",
    "Cloud Code": "Claude Code",
}


def fmt_time(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def load_turns(path: Path | None) -> list[dict]:
    if not path:
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def speaker_for(segment_id: int, turns: list[dict]) -> str:
    for turn in turns:
        if int(turn["start_id"]) <= segment_id <= int(turn["end_id"]):
            return str(turn["speaker"])
    return "说话人"


def clean_text(parts: list[str], corrections: dict[str, str]) -> str:
    text = " ".join(part.strip() for part in parts if part.strip())
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([，。！？、；：,.!?])", r"\1", text)
    text = text.replace(" ,", "，")
    for source, target in corrections.items():
        text = text.replace(source, target)
    return text.strip()


def add_grouped(grouped: list[dict], speaker: str, start: float, end: float, text: str) -> None:
    if grouped and grouped[-1]["speaker"] == speaker:
        grouped[-1]["end"] = end
        grouped[-1]["parts"].append(text)
        return
    grouped.append({"speaker": speaker, "start": start, "end": end, "parts": [text]})


def parse_drop_segments(values: list[str]) -> set[int]:
    dropped: set[int] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            dropped.add(int(part))
    return dropped


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Format Whisper JSON as speaker-labeled interview Markdown.")
    parser.add_argument("json_path", help="Whisper JSON file")
    parser.add_argument("--out", help="Output Markdown path")
    parser.add_argument("--source", help="Original source file path")
    parser.add_argument("--turns", help="JSON file mapping segment ID ranges to speakers")
    parser.add_argument("--title", default="面试文字记录")
    parser.add_argument("--corrections", help="Optional JSON dictionary of ASR corrections")
    parser.add_argument("--drop-segment", action="append", default=[], help="Segment ID(s) to omit, comma-separated allowed")
    parser.add_argument("--print-segments", action="store_true", help="Print segment IDs, times, and text, then exit")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    dropped = parse_drop_segments(args.drop_segment)

    segments = [segment for segment in data.get("segments", []) if int(segment.get("id", -1)) not in dropped]
    if args.print_segments:
        for segment in segments:
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
    if args.corrections:
        corrections.update(json.loads(Path(args.corrections).read_text(encoding="utf-8")))

    grouped: list[dict] = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        segment_id = int(segment["id"])
        speaker = speaker_for(segment_id, turns) if turns else "说话人"
        add_grouped(grouped, speaker, float(segment["start"]), float(segment["end"]), text)

    duration = max((float(s.get("end", 0)) for s in segments), default=0)
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
