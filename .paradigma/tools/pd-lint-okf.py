#!/usr/bin/env python3
"""Paradigma OKF linter.

No third-party dependencies are required. The parser intentionally supports the
small YAML subset used by Paradigma config, schema, and frontmatter files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import hashlib
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".paradigma" / "config.yaml"
SCHEMA_PATH = ROOT / ".paradigma" / "schemas" / "paradigma-types.schema.yaml"
RESERVED_FILENAMES = {"index.md", "log.md"}
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})$")
HEADING_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
BEGIN_MARKER = "<!-- BEGIN PARADIGMA AUTO-INDEX -->"
END_MARKER = "<!-- END PARADIGMA AUTO-INDEX -->"
CHECKSUM_PATTERN = re.compile(r"<!-- checksum:\s*([0-9a-f]+)\s*-->")


@dataclass
class LintIssue:
    level: str
    path: Path
    message: str

    def format(self) -> str:
        relative_path = self.path.relative_to(ROOT)
        return f"{self.level}: {relative_path}: {self.message}"


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
        key = key.strip()
        value = value.strip()
        stack = stack[:level]
        stack.append(key)
        full_key = ".".join(stack)
        if value:
            data[full_key] = parse_scalar(value)
        else:
            data.setdefault(full_key, [])

    return data


def read_yaml_file(path: Path) -> dict[str, str | list[str]]:
    return parse_yaml_subset(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def get_list(data: dict[str, str | list[str]], key: str) -> list[str]:
    value = data.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)] if value else []


def get_scalar(data: dict[str, str | list[str]], key: str) -> str:
    value = data.get(key, "")
    if isinstance(value, list):
        return ""
    return str(value).strip()


def load_config() -> dict[str, str | list[str]]:
    config = read_yaml_file(CONFIG_PATH)
    if not get_list(config, "knowledge_roots"):
        config["knowledge_roots"] = ["memory-bank/knowledge", "docs/rfc"]
    return config


def load_schema() -> dict[str, str | list[str]]:
    return read_yaml_file(SCHEMA_PATH)


def concept_types(schema: dict[str, str | list[str]]) -> set[str]:
    types: set[str] = set()
    for key in schema:
        if key.startswith("types."):
            _, document_type, *_ = key.split(".")
            types.add(document_type)
    return types


def schema_sections(schema: dict[str, str | list[str]], document_type: str) -> list[str]:
    return get_list(schema, f"types.{document_type}.required_sections")


def iter_markdown_files(config: dict[str, str | list[str]]) -> tuple[list[Path], list[Path]]:
    concepts: list[Path] = []
    indexes: list[Path] = []
    for root_text in get_list(config, "knowledge_roots"):
        root = ROOT / root_text
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name in RESERVED_FILENAMES:
                indexes.append(path)
            else:
                concepts.append(path)
    return concepts, indexes


def split_frontmatter(path: Path) -> tuple[dict[str, str | list[str]], str, str | None]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return {}, text, "missing YAML frontmatter"

    lines = text.splitlines()
    close_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_index = index
            break

    if close_index is None:
        return {}, text, "frontmatter is not closed"

    frontmatter = "\n".join(lines[1:close_index])
    body = "\n".join(lines[close_index + 1 :])
    return parse_yaml_subset(frontmatter), body, None


def has_required_sections(body: str, required_sections: list[str]) -> list[str]:
    headings = {match.group(1).strip() for match in HEADING_PATTERN.finditer(body)}
    return [section for section in required_sections if section not in headings]


def validate_document(path: Path, schema: dict[str, str | list[str]], mode: str) -> list[LintIssue]:
    metadata, body, error = split_frontmatter(path)
    if error:
        return [LintIssue("ERROR", path, error)]

    issues: list[LintIssue] = []
    document_type = get_scalar(metadata, "type")
    allowed_types = concept_types(schema)
    if not document_type:
        issues.append(LintIssue("ERROR", path, "frontmatter must include a non-empty `type` field"))
        return issues
    if allowed_types and document_type not in allowed_types:
        issues.append(LintIssue("ERROR", path, f"unknown type `{document_type}`"))

    required_frontmatter = get_list(schema, "required_frontmatter") if mode == "strict" else ["type"]
    for key in required_frontmatter:
        if not metadata.get(key):
            issues.append(LintIssue("ERROR", path, f"missing required frontmatter field `{key}`"))

    timestamp = get_scalar(metadata, "timestamp")
    if timestamp and not TIMESTAMP_PATTERN.match(timestamp):
        issues.append(LintIssue("ERROR", path, f"timestamp `{timestamp}` is not ISO 8601"))

    for key in get_list(schema, "required_paradigma_fields") if mode == "strict" else []:
        if not metadata.get(f"paradigma.{key}"):
            issues.append(LintIssue("ERROR", path, f"missing required paradigma field `{key}`"))

    enum_checks = [
        ("paradigma.update_policy", "allowed_update_policies"),
        ("paradigma.epistemic_status", "allowed_epistemic_statuses"),
        ("paradigma.temperature", "allowed_temperatures"),
        ("paradigma.lifecycle", "allowed_lifecycles"),
    ]
    for field, allowed_key in enum_checks:
        value = get_scalar(metadata, field)
        allowed = set(get_list(schema, allowed_key))
        if value and allowed and value not in allowed:
            issues.append(LintIssue("ERROR", path, f"invalid {field} `{value}`"))

    if mode == "strict":
        missing_sections = has_required_sections(body, schema_sections(schema, document_type))
        for section in missing_sections:
            issues.append(LintIssue("ERROR", path, f"missing required section `# {section}`"))

        if not metadata.get("paradigma.retrieval_hints.zh") and not metadata.get("paradigma.retrieval_hints.en"):
            issues.append(LintIssue("WARN", path, "retrieval_hints are missing"))
        has_relations = any(key.startswith("paradigma.relations.") for key in metadata)
        if not has_relations and "decision" not in document_type:
            issues.append(LintIssue("WARN", path, "relations are missing"))

    return issues


def validate_index(path: Path, mode: str) -> list[LintIssue]:
    text = path.read_text(encoding="utf-8-sig")
    begin_count = text.count(BEGIN_MARKER)
    end_count = text.count(END_MARKER)
    issues: list[LintIssue] = []
    if begin_count != end_count:
        issues.append(LintIssue("ERROR", path, "generated block markers are unbalanced"))
    if mode == "strict" and begin_count:
        between = text.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0].strip("\n")
        checksum_match = CHECKSUM_PATTERN.search(between)
        if not checksum_match:
            issues.append(LintIssue("WARN", path, "generated block checksum is missing"))
        else:
            inner_lines = [
                line for line in between.splitlines() if not CHECKSUM_PATTERN.match(line.strip())
            ]
            digest = hashlib.sha256("\n".join(inner_lines).encode("utf-8")).hexdigest()[:16]
            if digest != checksum_match.group(1):
                issues.append(LintIssue("ERROR", path, "generated block checksum is stale"))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="enforce schema fields and required sections")
    parser.add_argument("--normal", action="store_true", help="default mode: enforce hard OKF rules")
    parser.add_argument("--warn", action="store_true", help="report findings without failing")
    args = parser.parse_args()

    mode = "strict" if args.strict else "warn" if args.warn else "normal"
    config = load_config()
    schema = load_schema()
    concept_documents, index_documents = iter_markdown_files(config)

    issues: list[LintIssue] = []
    for document in concept_documents:
        issues.extend(validate_document(document, schema, mode))
    for index in index_documents:
        issues.extend(validate_index(index, mode))

    for issue in issues:
        print(issue.format())

    error_count = sum(1 for issue in issues if issue.level == "ERROR")
    warning_count = sum(1 for issue in issues if issue.level == "WARN")
    print(
        f"Checked {len(concept_documents)} OKF concept document(s) and {len(index_documents)} index/log file(s); "
        f"errors={error_count}, warnings={warning_count}, mode={mode}."
    )
    return 0 if mode == "warn" or error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
