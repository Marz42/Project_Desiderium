#!/usr/bin/env python3
"""Synchronize Paradigma knowledge indexes with retrieval-oriented metadata.

Reads knowledge_roots from .paradigma/config.yaml and generates an index.md for
each root and each subdirectory that contains concept documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import hashlib
import sys


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".paradigma" / "config.yaml"
RESERVED_FILENAMES = {"index.md", "log.md"}
BEGIN_MARKER = "<!-- BEGIN PARADIGMA AUTO-INDEX -->"
END_MARKER = "<!-- END PARADIGMA AUTO-INDEX -->"
GENERATED_BY = "<!-- generated_by: pd-sync-index.py -->"


@dataclass
class Concept:
    path: Path
    document_type: str
    title: str
    description: str
    hints: list[str]
    symbols: list[str]
    relations: list[str]


def parse_scalar(value: str) -> str | list[str]:
    value = value.strip().strip('"').strip("'")
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",")]
    return value


def parse_yaml_subset(text: str) -> dict[str, str | list[str]]:
    data: dict[str, str | list[str]] = {}
    stack: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        level = indent // 2
        line = raw_line.strip()
        if line.startswith("- "):
            key = ".".join(stack)
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(parse_scalar(line[2:].strip()))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        stack = stack[:level]
        stack.append(key.strip())
        full_key = ".".join(stack)
        data[full_key] = parse_scalar(value) if value.strip() else []
    return data


def read_yaml_file(path: Path) -> dict[str, str | list[str]]:
    return parse_yaml_subset(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def get_list(data: dict[str, str | list[str]], key: str) -> list[str]:
    value = data.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)] if value else []


def knowledge_roots() -> list[Path]:
    config = read_yaml_file(CONFIG_PATH)
    roots = get_list(config, "knowledge_roots") or ["memory-bank/knowledge"]
    return [(ROOT / root_text).resolve() for root_text in roots]


def parse_frontmatter(path: Path) -> dict[str, str | list[str]]:
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


def get_scalar(metadata: dict[str, str | list[str]], key: str, default: str = "") -> str:
    value = metadata.get(key, default)
    return "" if isinstance(value, list) else str(value).strip()


def relation_summary(metadata: dict[str, str | list[str]]) -> list[str]:
    summary: list[str] = []
    for key, value in metadata.items():
        if not key.startswith("paradigma.relations."):
            continue
        relation = key.rsplit(".", 1)[-1]
        values = value if isinstance(value, list) else [value]
        for item in values:
            target = str(item).strip()
            if target:
                summary.append(f"{relation}:{target}")
    return summary


def collect_concepts(scope: Path) -> list[Concept]:
    concepts: list[Concept] = []
    if not scope.exists():
        return concepts
    for path in sorted(scope.rglob("*.md")):
        if path.name in RESERVED_FILENAMES:
            continue
        metadata = parse_frontmatter(path)
        document_type = get_scalar(metadata, "type")
        if not document_type:
            continue
        hints = get_list(metadata, "paradigma.retrieval_hints.zh") + get_list(metadata, "paradigma.retrieval_hints.en")
        concepts.append(
            Concept(
                path=path,
                document_type=document_type,
                title=get_scalar(metadata, "title", path.stem) or path.stem,
                description=get_scalar(metadata, "description"),
                hints=hints,
                symbols=get_list(metadata, "paradigma.symbols"),
                relations=relation_summary(metadata),
            )
        )
    return concepts


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def summarize(values: list[str], limit: int = 3) -> str:
    if not values:
        return "-"
    clipped = values[:limit]
    suffix = " ..." if len(values) > limit else ""
    return "<br>".join(escape_cell(value) for value in clipped) + suffix


def safe_relative_link(target: Path, index_path: Path) -> str:
    try:
        return target.relative_to(index_path.parent).as_posix()
    except ValueError:
        for root in knowledge_roots():
            try:
                return target.relative_to(root).as_posix()
            except ValueError:
                continue
        return target.name


def render_inner(concepts: list[Concept], index_path: Path) -> list[str]:
    lines = [
        GENERATED_BY,
        "",
        "| Path | Type | Title | Hints | Symbols | Relations |",
        "|------|------|-------|-------|---------|-----------|",
    ]
    for concept in concepts:
        path_text = safe_relative_link(concept.path, index_path)
        lines.append(
            "| "
            f"[{path_text}]({path_text}) | "
            f"`{escape_cell(concept.document_type)}` | "
            f"{escape_cell(concept.title)} | "
            f"{summarize(concept.hints)} | "
            f"{summarize(concept.symbols)} | "
            f"{summarize(concept.relations, limit=4)} |"
        )
    return lines


def checksum(inner_lines: list[str]) -> str:
    return hashlib.sha256("\n".join(inner_lines).encode("utf-8")).hexdigest()[:16]


def render_generated_block(concepts: list[Concept], index_path: Path) -> str:
    inner = render_inner(concepts, index_path)
    digest = checksum(inner)
    return "\n".join([BEGIN_MARKER, f"<!-- checksum: {digest} -->", *inner, "", END_MARKER])


def replace_generated_block(existing: str, block: str) -> str:
    if BEGIN_MARKER in existing and END_MARKER in existing:
        before = existing.split(BEGIN_MARKER, 1)[0].rstrip()
        after = existing.split(END_MARKER, 1)[1].lstrip()
        return f"{before}\n\n{block}\n\n{after}".rstrip() + "\n"
    return existing.rstrip() + "\n\n" + block + "\n"


def desired_index_content(index_path: Path, concepts: list[Concept], title: str) -> str:
    existing = index_path.read_text(encoding="utf-8-sig") if index_path.exists() else f"# {title}\n"
    return replace_generated_block(existing, render_generated_block(concepts, index_path))


def subdirectories(knowledge_root: Path) -> list[str]:
    if not knowledge_root.exists():
        return []
    dirs = []
    for sub in sorted(knowledge_root.iterdir()):
        if sub.is_dir() and any(sub.rglob("*.md")):
            dirs.append(sub.name)
    return dirs


def index_targets() -> list[tuple[Path, Path, str]]:
    targets: list[tuple[Path, Path, str]] = []
    for root in knowledge_roots():
        if not root.exists():
            continue
        root_title = root.name.title() + " Index"
        targets.append((root, root / "index.md", root_title))
        for sub in subdirectories(root):
            scope = root / sub
            targets.append((scope, scope / "index.md", f"{sub.title()} Index"))
    return targets


def write_indexes() -> int:
    updated = 0
    for scope, index_path, title in index_targets():
        concepts = collect_concepts(scope)
        desired = desired_index_content(index_path, concepts, title)
        current = index_path.read_text(encoding="utf-8-sig") if index_path.exists() else ""
        if current != desired:
            index_path.write_text(desired, encoding="utf-8", newline="\n")
            updated += 1
        print(f"Indexed {len(concepts)} concept(s) into {index_path.relative_to(ROOT)}")
    return updated


def check_indexes() -> int:
    stale = 0
    for scope, index_path, title in index_targets():
        concepts = collect_concepts(scope)
        desired = desired_index_content(index_path, concepts, title)
        current = index_path.read_text(encoding="utf-8-sig") if index_path.exists() else ""
        if current != desired:
            print(f"STALE: {index_path.relative_to(ROOT)}")
            stale += 1
        else:
            print(f"OK: {index_path.relative_to(ROOT)}")
    return stale


def print_inventory() -> None:
    total = 0
    for root in knowledge_roots():
        concepts = collect_concepts(root)
        total += len(concepts)
        for concept in concepts:
            rel = concept.path.relative_to(root).as_posix()
            print(f"{root.name}/{rel}\t{concept.document_type}\t{concept.title}\t{summarize(concept.hints)}")
    print(f"Found {total} concept(s) across {len(knowledge_roots())} knowledge root(s). Use --write to update indexes or --check to verify them.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="rewrite generated blocks in root and subdirectory indexes")
    parser.add_argument("--check", action="store_true", help="fail if generated index blocks are stale")
    args = parser.parse_args()

    if args.write and args.check:
        parser.error("--write and --check are mutually exclusive")
    if args.write:
        updated = write_indexes()
        print(f"Updated {updated} index file(s).")
        return 0
    if args.check:
        stale = check_indexes()
        print(f"Checked indexes; stale={stale}.")
        return 1 if stale else 0
    print_inventory()
    return 0


if __name__ == "__main__":
    sys.exit(main())
