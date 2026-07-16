#!/usr/bin/env python3
"""Diagnose Paradigma Harness gaps between a project and the latest upstream.

Detection rules (try in order):
  1. .paradigma/config.yaml with paradigma_harness_version -> read version
  2. memory_bank/ (underscore) directory exists      -> "pre-0.2.0 (legacy flat)"
  3. memory-bank/ exists but no runtime/ subdirectory -> "0.2.x (flat memory-bank)"
  4. memory-bank/runtime/ exists                     -> "0.3.0+ (OKF three-state)"
  5. None of the above                               -> "no Paradigma harness detected"

Once version is identified, compare against upstream to find gaps in:
  - Structure (directories)
  - Tools (.paradigma/tools/*.py)
  - Schema (.paradigma/schemas/*.yaml)
  - Config (.paradigma/config.yaml keys)
  - Protocol (AGENT_RULES.md, INIT_PROMPT.md, .cursor/rules/)

Exit codes:
  0 - version matches upstream (no gaps)
  1 - version mismatch or gaps found
  2 - Paradigma harness not detected
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


# -- data model --------------------------------------------------


@dataclass
class Gap:
    category: str
    severity: str
    kind: str
    item: str
    detail: str = ""


@dataclass
class DiagnoseResult:
    project_path: Path
    upstream_path: Path
    detected_version: str
    upstream_version: str
    version_match: bool
    gaps: list[Gap] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for g in self.gaps if g.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for g in self.gaps if g.severity == "warning")

    @property
    def infos(self) -> int:
        return sum(1 for g in self.gaps if g.severity == "info")

    def to_dict(self) -> dict:
        return {
            "project_path": str(self.project_path),
            "upstream_path": str(self.upstream_path),
            "detected_version": self.detected_version,
            "upstream_version": self.upstream_version,
            "version_match": self.version_match,
            "gaps": [
                {"category": g.category, "severity": g.severity,
                 "kind": g.kind, "item": g.item, "detail": g.detail}
                for g in self.gaps
            ],
            "summary": {
                "errors": self.errors,
                "warnings": self.warnings,
                "infos": self.infos,
                "total": len(self.gaps),
            }
        }


# -- version detection -------------------------------------------


def _read_yaml_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _detect_version(project: Path) -> str:
    config = project / ".paradigma" / "config.yaml"
    if config.exists():
        data = _read_yaml_file(config)
        version = data.get("paradigma_harness_version", "")
        if version:
            return version

    if (project / "memory_bank").is_dir():
        return "pre-0.2.0 (legacy flat memory_bank/)"

    mb = project / "memory-bank"
    if mb.is_dir():
        if (mb / "runtime").is_dir():
            return "0.3.0+ (OKF three-state, exact version unknown)"
        return "0.2.x (flat memory-bank/)"

    return "unknown"


def _read_upstream_version(upstream: Path) -> str:
    data = _read_yaml_file(upstream / ".paradigma" / "config.yaml")
    version = data.get("paradigma_harness_version", "")
    if version:
        return version
    ver_file = upstream / "VERSION"
    if ver_file.exists():
        return ver_file.read_text(encoding="utf-8").strip()
    return "unknown"


# -- comparison helpers ------------------------------------------


def _file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _list_py_files(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {p.name for p in directory.glob("*.py")}


def _list_yaml_files(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {p.name for p in directory.glob("*.yaml")}


# -- structure check ---------------------------------------------


_REQUIRED_DIRS = [
    ("memory-bank/runtime", "运行态目录"),
    ("memory-bank/logs", "日志目录"),
    ("memory-bank/knowledge", "知识库目录"),
    ("memory-bank-template", "模板源目录"),
    (".paradigma/schemas", "Schema 目录"),
]

_REQUIRED_LOGS_DIRS = [
    ("memory-bank/logs/progress", "会话日志目录"),
]


def _check_structure(project: Path, result: DiagnoseResult) -> None:
    for rel, desc in _REQUIRED_DIRS:
        if not (project / rel).is_dir():
            result.gaps.append(Gap(
                "structure", "error", "missing",
                f"目录缺失: {rel}",
                f"用途: {desc}",
            ))

    for rel, desc in _REQUIRED_LOGS_DIRS:
        p = project / rel
        if not p.is_dir() and (project / "memory-bank" / "logs").is_dir():
            result.gaps.append(Gap(
                "structure", "warning", "missing",
                f"子目录缺失: {rel}",
                f"用途: {desc}",
            ))


# -- tools check -------------------------------------------------


def _check_tools(project: Path, upstream: Path, result: DiagnoseResult) -> None:
    up_tools = _list_py_files(upstream / ".paradigma" / "tools")
    proj_tools = _list_py_files(project / ".paradigma" / "tools")

    if not up_tools:
        return

    if not proj_tools:
        result.gaps.append(Gap(
            "tools", "error", "missing",
            "工具链完全缺失",
            f"上游有 {len(up_tools)} 个工具: {', '.join(sorted(up_tools))}",
        ))
        return

    missing = up_tools - proj_tools
    if missing:
        result.gaps.append(Gap(
            "tools", "warning", "missing",
            f"缺少 {len(missing)} 个工具",
            ", ".join(sorted(missing)),
        ))

    for tool_name in sorted(up_tools & proj_tools):
        up_hash = _file_hash(upstream / ".paradigma" / "tools" / tool_name)
        proj_hash = _file_hash(project / ".paradigma" / "tools" / tool_name)
        if up_hash and proj_hash and up_hash != proj_hash:
            result.gaps.append(Gap(
                "tools", "warning", "outdated",
                f"工具内容已变更: {tool_name}",
                "与上游版本不一致，建议更新",
            ))

    extra = proj_tools - up_tools
    if extra:
        result.gaps.append(Gap(
            "tools", "info", "extra",
            f"项目自建工具: {', '.join(sorted(extra))}",
            "这些文件不在上游白名单中，不会被覆盖",
        ))


# -- schema check ------------------------------------------------


def _check_schema(project: Path, upstream: Path, result: DiagnoseResult) -> None:
    up_schemas = _list_yaml_files(upstream / ".paradigma" / "schemas")
    proj_schemas = _list_yaml_files(project / ".paradigma" / "schemas")

    if not up_schemas:
        return

    if not proj_schemas:
        result.gaps.append(Gap(
            "schema", "error", "missing",
            "Schema 完全缺失",
            f"上游有 {len(up_schemas)} 个 schema 文件",
        ))
        return

    missing = up_schemas - proj_schemas
    if missing:
        result.gaps.append(Gap(
            "schema", "warning", "missing",
            f"缺少 {len(missing)} 个 schema",
            ", ".join(sorted(missing)),
        ))

    for schema_name in sorted(up_schemas & proj_schemas):
        up_hash = _file_hash(upstream / ".paradigma" / "schemas" / schema_name)
        proj_hash = _file_hash(project / ".paradigma" / "schemas" / schema_name)
        if up_hash and proj_hash and up_hash != proj_hash:
            result.gaps.append(Gap(
                "schema", "warning", "outdated",
                f"Schema 内容已变更: {schema_name}",
                "与上游版本不一致，可能新增了类型定义",
            ))


# -- config check ------------------------------------------------


def _check_config(project: Path, upstream: Path, result: DiagnoseResult) -> None:
    up_cfg = upstream / ".paradigma" / "config.yaml"
    proj_cfg = project / ".paradigma" / "config.yaml"

    if not up_cfg.exists():
        return

    if not proj_cfg.exists():
        result.gaps.append(Gap(
            "config", "error", "missing",
            ".paradigma/config.yaml 不存在",
            "需从上游复制并配置项目特定参数",
        ))
        return

    up_data = _read_yaml_file(up_cfg)
    proj_data = _read_yaml_file(proj_cfg)

    up_keys = set(up_data.keys())
    proj_keys = set(proj_data.keys())

    missing_keys = up_keys - proj_keys
    if missing_keys:
        result.gaps.append(Gap(
            "config", "warning", "missing",
            f"配置缺少 {len(missing_keys)} 个字段",
            ", ".join(sorted(missing_keys)),
        ))

    version_key = "paradigma_harness_version"
    if version_key in proj_data and version_key in up_data:
        if proj_data[version_key] != up_data[version_key]:
            result.gaps.append(Gap(
                "config", "warning", "mismatch",
                "paradigma_harness_version 不匹配",
                f"项目: {proj_data[version_key]}, 上游: {up_data[version_key]}",
            ))


# -- protocol check ----------------------------------------------


_PROTOCOL_FILES = [
    "AGENT_RULES.md",
    "INIT_PROMPT.md",
    ".cursor/rules/memory-bank-protocol.mdc",
]


def _check_protocol(project: Path, upstream: Path, result: DiagnoseResult) -> None:
    for rel in _PROTOCOL_FILES:
        proj_file = project / rel
        up_file = upstream / rel

        if not up_file.exists():
            continue

        if not proj_file.exists():
            result.gaps.append(Gap(
                "protocol", "error", "missing",
                f"协议文件缺失: {rel}",
                "需从上游复制",
            ))
            continue

        up_hash = _file_hash(up_file)
        proj_hash = _file_hash(proj_file)

        if up_hash != proj_hash:
            result.gaps.append(Gap(
                "protocol", "info", "mismatch",
                f"协议文件差异: {rel}",
                "此文件可能已被项目自定义修改。请手动审查差异，不可自动覆盖。",
            ))


# -- main --------------------------------------------------------


def diagnose(project: Path, upstream: Path) -> DiagnoseResult:
    detected = _detect_version(project)
    upstream_ver = _read_upstream_version(upstream)
    version_match = (detected == upstream_ver)

    result = DiagnoseResult(
        project_path=project.resolve(),
        upstream_path=upstream.resolve(),
        detected_version=detected,
        upstream_version=upstream_ver,
        version_match=version_match,
    )

    if detected == "unknown":
        result.gaps.append(Gap(
            "structure", "error", "missing",
            "未检测到 Paradigma Harness",
            "项目不包含 memory-bank/ 或 memory_bank/ 目录",
        ))
        return result

    if not version_match:
        result.gaps.append(Gap(
            "config", "error", "mismatch",
            f"版本不匹配: {detected} vs {upstream_ver}",
            f"需将项目从 {detected} 更新到 {upstream_ver}",
        ))

    _check_structure(project, result)
    _check_tools(project, upstream, result)
    _check_schema(project, upstream, result)
    _check_config(project, upstream, result)
    _check_protocol(project, upstream, result)

    return result


def _format_human(result: DiagnoseResult) -> str:
    lines: list[str] = []
    sep = "=" * 62

    lines.append(sep)
    lines.append("  Paradigma Harness 诊断报告")
    lines.append(f"  项目: {result.project_path}")
    lines.append(f"  检测版本: {result.detected_version}")
    lines.append(f"  上游版本: {result.upstream_version}")
    if result.version_match:
        lines.append("  状态: [OK] 版本一致")
    else:
        lines.append("  状态: [!] 版本不一致，需要更新")
    lines.append(sep)
    lines.append("")

    if not result.gaps:
        lines.append("[OK] 未检测到差距。项目与上游 Paradigma 一致。")
        return "\n".join(lines)

    by_cat: dict[str, list[Gap]] = {}
    category_order = ["structure", "tools", "schema", "config", "protocol"]
    cat_labels = {
        "structure": "目录结构",
        "tools": "工具链",
        "schema": "Schema",
        "config": "配置",
        "protocol": "协议文件",
    }
    sev_icons = {"error": "[ERR]", "warning": "[WARN]", "info": "[INFO]"}

    for gap in result.gaps:
        by_cat.setdefault(gap.category, []).append(gap)

    for cat in category_order:
        if cat not in by_cat:
            continue
        cat_gaps = by_cat[cat]
        label = cat_labels.get(cat, cat)
        sev_counts: dict[str, int] = {}
        for g in cat_gaps:
            sev_counts[g.severity] = sev_counts.get(g.severity, 0) + 1
        summary = ", ".join(
            f"{sev_icons.get(s, s)} x{c}" for s, c in sorted(sev_counts.items())
        )
        lines.append(f"{summary}  {label} ({len(cat_gaps)} 项)")
        for g in cat_gaps:
            if g.kind in ("missing",):
                prefix = "  -"
            elif g.kind in ("mismatch", "outdated"):
                prefix = "  ~"
            elif g.kind == "extra":
                prefix = "  +"
            else:
                prefix = "  ?"
            lines.append(f"{prefix} {g.item}")
            if g.detail:
                lines.append(f"     {g.detail}")
        lines.append("")

    lines.append(sep)
    lines.append(
        f"  合计: {result.errors} errors, {result.warnings} warnings, "
        f"{result.infos} infos"
    )
    lines.append("")

    if result.errors > 0:
        lines.append("建议操作:")
        has_struct = any(
            g.category == "structure" and g.severity == "error"
            for g in result.gaps
        )
        has_tools = any(
            g.category == "tools" and g.severity in ("error", "warning")
            for g in result.gaps
        )
        has_cfg = any(
            g.category == "config" and g.kind == "missing"
            for g in result.gaps
        )
        has_proto = any(g.category == "protocol" for g in result.gaps)

        if has_struct:
            lines.append("  1. 使用 INIT_PROMPT 模式 H 进行 Agent 引导的结构迁移")
        if has_tools:
            lines.append("  2. 从上游复制工具链 (.paradigma/tools/) 和 Schema (.paradigma/schemas/)")
        if has_cfg:
            lines.append("  3. 从上游复制 .paradigma/config.yaml 并配置项目特定参数")
        if has_proto:
            lines.append("  4. 手动审查协议文件差异 (AGENT_RULES.md / INIT_PROMPT.md / .cursor/rules/)")
        lines.append("  5. 完成后运行 pd-check-all.py 校验")
        lines.append("  6. 更新 .paradigma/config.yaml 中的 paradigma_harness_version")
    elif result.warnings > 0:
        lines.append("建议: 从上游更新缺失/过时的工具和 Schema。协议文件差异较小，可手动审查。")

    lines.append(sep)
    return "\n".join(lines)


def _check_version_only(project: Path, upstream: Path) -> int:
    detected = _detect_version(project)
    upstream_ver = _read_upstream_version(upstream)
    return 0 if detected == upstream_ver else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose Paradigma Harness gaps between project and upstream."
    )
    parser.add_argument(
        "--upstream", required=True,
        help="Path to Paradigma upstream source (latest version)."
    )
    parser.add_argument(
        "--project", default=".",
        help="Path to project directory (default: current directory)."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output machine-readable JSON."
    )
    parser.add_argument(
        "--check-version", action="store_true",
        help="Quick version-only check (exit 0=match, 1=mismatch)."
    )

    args = parser.parse_args()

    project = Path(args.project).resolve()
    upstream = Path(args.upstream).resolve()

    if not upstream.is_dir():
        print(f"ERROR: upstream path does not exist: {upstream}", file=sys.stderr)
        return 2

    if not project.is_dir():
        print(f"ERROR: project path does not exist: {project}", file=sys.stderr)
        return 2

    if args.check_version:
        return _check_version_only(project, upstream)

    result = diagnose(project, upstream)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(_format_human(result))

    if result.detected_version == "unknown":
        return 2
    if result.errors > 0:
        return 1
    if result.warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
