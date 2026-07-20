#!/usr/bin/env python3
"""Offline migration head verification.

Confirms that the Alembic migration chain ends at the expected head revision
without requiring a live database.  Run from the project root:

    python scripts/check_migration_head.py

Exit 0 = head matches; exit 1 = mismatch or parse error.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

EXPECTED_HEAD = "a7b8c9d0e1f2"
VERSIONS_DIR = Path(__file__).parent.parent / "migrations" / "versions"


def load_revision_info(path: Path) -> dict[str, str | None]:
    """Extract revision and down_revision from a migration file using regex."""
    text = path.read_text()
    rev_match = re.search(r'^revision\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    down_match = re.search(r'^down_revision\s*=\s*(?:["\']([^"\']*)["\']|None)', text, re.MULTILINE)
    return {
        "revision": rev_match.group(1) if rev_match else None,
        "down_revision": down_match.group(1) if down_match and down_match.group(1) else None,
    }


def find_head(versions_dir: Path) -> str | None:
    """Return the revision that no other revision points to as its parent."""
    all_files = list(versions_dir.glob("*.py"))
    revisions: dict[str, str | None] = {}
    for f in all_files:
        info = load_revision_info(f)
        if info["revision"]:
            revisions[info["revision"]] = info["down_revision"]

    referenced_as_parent = set(revisions.values()) - {None}
    heads = [rev for rev in revisions if rev not in referenced_as_parent]
    return heads[0] if len(heads) == 1 else None


def main() -> int:
    head = find_head(VERSIONS_DIR)
    if head is None:
        print("ERROR: could not determine a unique migration head.", file=sys.stderr)
        return 1
    if head != EXPECTED_HEAD:
        print(
            f"FAIL: migration head is '{head}', expected '{EXPECTED_HEAD}'.",
            file=sys.stderr,
        )
        return 1
    print(f"OK: migration head is '{head}' as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
