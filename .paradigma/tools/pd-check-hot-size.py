#!/usr/bin/env python3
"""Report HOT memory and runtime file sizes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import sys


ROOT = Path(__file__).resolve().parents[2]
ACTIVE_TASK = ROOT / "memory-bank" / "runtime" / "active-task.md"
KNOWLEDGE_ROOT = ROOT / "memory-bank" / "knowledge"
PROGRESS_INDEX = ROOT / "memory-bank" / "logs" / "progress" / "index.md"


@dataclass
class SizeCheck:
    path: Path
    lines: int
    warn_at: int
    error_at: int
    category: str

    @property
    def level(self) -> str:
        if self.lines > self.error_at:
            return "ERROR"
        if self.lines > self.warn_at:
            return "WARN"
        return "OK"

    def format(self) -> str:
        return f"{self.level}: {self.path.relative_to(ROOT)}: {self.lines} lines ({self.category}; warn>{self.warn_at}, error>{self.error_at})"


def parse_yaml_subset(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    stack: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        level = indent // 2
        line = raw_line.strip()
        if line.startswith("- ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        stack = stack[:level]
        stack.append(key.strip())
        if value.strip():
            metadata[".".join(stack)] = value.strip().strip('"').strip("'")
    return metadata


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    close_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_index = index
            break
    if close_index is None:
        return {}
    return parse_yaml_subset("\n".join(lines[1:close_index]))


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8-sig").splitlines()) if path.exists() else 0


def hot_documents() -> list[Path]:
    documents: list[Path] = []
    if not KNOWLEDGE_ROOT.exists():
        return documents
    for path in sorted(KNOWLEDGE_ROOT.rglob("*.md")):
        if path.name in {"index.md", "log.md"}:
            continue
        if frontmatter(path).get("paradigma.temperature") == "hot":
            documents.append(path)
    return documents


def collect_checks() -> list[SizeCheck]:
    checks: list[SizeCheck] = []
    if ACTIVE_TASK.exists():
        checks.append(SizeCheck(ACTIVE_TASK, line_count(ACTIVE_TASK), 160, 260, "runtime active task"))
    if PROGRESS_INDEX.exists():
        checks.append(SizeCheck(PROGRESS_INDEX, line_count(PROGRESS_INDEX), 160, 260, "progress index"))
    for path in hot_documents():
        checks.append(SizeCheck(path, line_count(path), 260, 420, "HOT knowledge"))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-warn", action="store_true", help="return non-zero when any warning is present")
    args = parser.parse_args()

    checks = collect_checks()
    for check in checks:
        print(check.format())
    errors = sum(1 for check in checks if check.level == "ERROR")
    warnings = sum(1 for check in checks if check.level == "WARN")
    print(f"Checked {len(checks)} HOT/runtime file(s); errors={errors}, warnings={warnings}.")
    return 1 if errors or (warnings and args.fail_on_warn) else 0


if __name__ == "__main__":
    sys.exit(main())
