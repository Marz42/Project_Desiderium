#!/usr/bin/env python3
"""Run all Paradigma quality-gate checks in sequence.

Equivalent to the Update Phase command sequence:
  pd-lint-okf.py --strict
  pd-check-links.py
  pd-sync-index.py --check
  pd-check-hot-size.py
  DESIGN.md basic validation (if present)

Stops on the first failure unless --keep-going is passed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / ".paradigma" / "tools"

STEPS = [
    ("lint", "pd-lint-okf.py", ["--strict"]),
    ("links", "pd-check-links.py", ["--allow-warnings"]),
    ("index", "pd-sync-index.py", ["--check"]),
    ("hot-size", "pd-check-hot-size.py", []),
]


def _check_design_md() -> bool:
    """Basic DESIGN.md validation. Returns True if OK or not present."""
    design_path = ROOT / "DESIGN.md"
    if not design_path.exists():
        return True  # No frontend — skip silently.

    content = design_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Check 1: has YAML frontmatter delimiters
    has_opening = any(line.strip() == "---" for line in lines[:5])
    if not has_opening:
        print("  WARNING: DESIGN.md exists but has no YAML frontmatter (missing --- delimiter).")
        return True  # Warning only, don't block.

    # Check 2: has at least colors and typography tokens
    lower = content.lower()
    issues = []
    if "colors:" not in lower:
        issues.append("colors")
    if "typography:" not in lower:
        issues.append("typography")
    if issues:
        print(f"  WARNING: DESIGN.md may be missing token sections: {', '.join(issues)}.")
    else:
        # Count approximate token definitions
        color_count = content.count("#")  # Rough: count hex color occurrences
        font_count = content.lower().count("fontfamily:")
        print(f"  OK: DESIGN.md found ({color_count} color hints, {font_count} font declarations).")
        print("  HINT: For deep validation, run: npx @google/design.md lint DESIGN.md")
    return True


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Run all Paradigma quality-gate checks.")
    parser.add_argument("--keep-going", action="store_true",
                        help="run all steps even after a failure")
    args = parser.parse_args()

    failures = 0
    total = len(STEPS) + 1  # +1 for DESIGN.md check

    for name, script, extra_args in STEPS:
        print(f"--- {name} ({script}) ---")
        cmd = [sys.executable, str(TOOLS / script)] + extra_args
        result = subprocess.run(cmd, cwd=str(ROOT))
        if result.returncode != 0:
            failures += 1
            print(f"  FAILED (exit {result.returncode})")
            if not args.keep_going:
                print(f"\n{failures}/{total} check(s) failed (stopped early).")
                return 1
        else:
            print(f"  OK")
        print()

    # DESIGN.md check (always warn-only, never fails)
    print("--- design (DESIGN.md) ---")
    _check_design_md()
    print()

    if failures:
        print(f"{failures}/{total} check(s) failed.")
        return 1
    print(f"All {total} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
