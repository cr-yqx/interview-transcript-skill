from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GLOSSARY_PATH = SKILL_DIR / "references" / "glossary.json"

SENSITIVE_PATTERNS = [
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(token|secret|password|passwd|api\s*key)\b", re.IGNORECASE),
    re.compile(r"^sessdata$", re.IGNORECASE),
    re.compile(r"sessdata\s*=", re.IGNORECASE),
    re.compile(r"(候选人|面试内容|账号|令牌|本机路径|个人项目链接)"),
]


def read_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected a JSON object: {path}")
    return data


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def has_sensitive_shape(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)


def sorted_unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return sorted(result, key=lambda item: item.casefold())


def parse_correction(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise SystemExit(f"Correction must use SOURCE=TARGET format: {value}")
    source, target = value.split("=", 1)
    source = normalize_text(source)
    target = normalize_text(target)
    if not source or not target:
        raise SystemExit(f"Correction source and target cannot be empty: {value}")
    if has_sensitive_shape(source) or has_sensitive_shape(target):
        raise SystemExit(f"Correction looks sensitive and was rejected: {value}")
    return source, target


def public_terms_from_candidates(candidates: dict) -> tuple[list[str], list[str]]:
    public_terms = candidates.get("public_terms", [])
    local_only_terms = {normalize_text(term) for term in candidates.get("local_only_terms", [])}
    if not isinstance(public_terms, list):
        raise SystemExit("glossary_candidates.json field public_terms must be a list")

    accepted: list[str] = []
    rejected: list[str] = []
    for raw_term in public_terms:
        term = normalize_text(raw_term)
        if not term:
            continue
        if term in local_only_terms or has_sensitive_shape(term):
            rejected.append(term)
            continue
        accepted.append(term)
    return sorted_unique(accepted), sorted_unique(rejected)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Merge human-confirmed public glossary candidates into references/glossary.json."
    )
    parser.add_argument("candidates", help="Path to job-level glossary_candidates.json")
    parser.add_argument("--glossary", default=str(DEFAULT_GLOSSARY_PATH), help="Target glossary JSON")
    parser.add_argument(
        "--correction",
        action="append",
        default=[],
        help="Manually add one safe public ASR correction in SOURCE=TARGET format. Can be repeated.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the merge result without writing")
    args = parser.parse_args()

    candidates_path = Path(args.candidates)
    glossary_path = Path(args.glossary)
    candidates = read_json(candidates_path)
    glossary = read_json(glossary_path)

    accepted_terms, rejected_terms = public_terms_from_candidates(candidates)
    existing_terms = [normalize_text(term) for term in glossary.get("public_terms", [])]
    merged_terms = sorted_unique(existing_terms + accepted_terms)

    corrections = glossary.get("corrections", {})
    if not isinstance(corrections, dict):
        raise SystemExit("Target glossary field corrections must be a JSON object")
    merged_corrections = {normalize_text(k): normalize_text(v) for k, v in corrections.items()}
    for item in args.correction:
        source, target = parse_correction(item)
        merged_corrections[source] = target

    updated = dict(glossary)
    updated["public_terms"] = merged_terms
    updated["corrections"] = dict(sorted(merged_corrections.items(), key=lambda item: item[0].casefold()))

    print(f"Accepted public terms: {len(accepted_terms)}")
    print(f"New public terms: {len(set(accepted_terms) - set(existing_terms))}")
    if rejected_terms:
        print("Rejected suspicious/local terms:")
        for term in rejected_terms:
            print(f"- {term}")

    if args.dry_run:
        print(json.dumps(updated, ensure_ascii=False, indent=2))
        return

    glossary_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {glossary_path}")


if __name__ == "__main__":
    main()
