#!/usr/bin/env python3
"""Lint protocol Markdown files for unfilled placeholders.

Scans tracked Markdown files and flags:
- `[填写...]` / `\\[填写...\\]` placeholders
- Literal `YYYY-MM-DD` / `YYYY-Www` / `NNN` left in non-template files
- EXP IDs that don't match `EXP-YYYYWww-NNN` format
- Discussion files closed (status: Resolved) without a Decision line

Exit code: 0 = clean, 1 = issues found.

Usage:
    python tools/lint_protocol.py            # lint all
    python tools/lint_protocol.py LOGS/      # lint subset
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Files where placeholders are expected (templates) — suppress those warnings.
TEMPLATE_FILES = {
    "bootstrap.md",
    "Discussion.md",
    "Discussion/Archive/README.md",
    "discussion/Archive/README.md",
    "MODE.md",
    "idea.md",
    "method.md",
    "LOGS/README.md",
    "tools/new_week.py",
    "tools/new_exp.py",
    "tools/lint_protocol.py",
    "tools/README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    # Legacy/local templates retained from the pre-merge repository.
    "idea/idea.md",
    "idea/idea-template.md",
}

PLACEHOLDER_RE = re.compile(r"\\?\[填写[^\]]*\\?\]")
DATE_PLACEHOLDER_RE = re.compile(r"YYYY-MM-DD")
WEEK_PLACEHOLDER_RE = re.compile(r"YYYY-Www|YYYYWww")
EXP_RE = re.compile(r"EXP-(\d{4})W(\d{2})-(\d{3})")
EXP_BAD_RE = re.compile(r"EXP-(?!\d{4}W\d{2}-\d{3})\S+")


def relevant_md_files(roots: list[Path]) -> list[Path]:
    files = []
    for root in roots:
        if root.is_file() and root.suffix == ".md":
            files.append(root)
        elif root.is_dir():
            files.extend(p for p in root.rglob("*.md") if ".git" not in p.parts)
    return files


def lint(path: Path) -> list[str]:
    rel = path.relative_to(REPO).as_posix()
    is_template = rel in TEMPLATE_FILES
    issues: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    if not is_template:
        for m in PLACEHOLDER_RE.finditer(text):
            issues.append(f"{rel}: unfilled placeholder {m.group(0)!r}")
        for m in DATE_PLACEHOLDER_RE.finditer(text):
            issues.append(f"{rel}: literal 'YYYY-MM-DD' left in non-template file")
        for m in WEEK_PLACEHOLDER_RE.finditer(text):
            issues.append(f"{rel}: literal week placeholder left in non-template file")

    for m in EXP_BAD_RE.finditer(text):
        token = m.group(0)
        if EXP_RE.match(token):
            continue
        if any(stub in token for stub in ("YYYYWww", "NNN", "...", "ID")):
            continue
        issues.append(f"{rel}: malformed EXP id {token!r} (expect EXP-YYYYWww-NNN)")

    if rel.startswith(("Discussion", "discussion")) and re.search(r"\|\s*\*\*状态 \(Status\)\*\*\s*\|\s*`?Resolved`?\s*\|", text):
        if "Decision" not in text or re.search(r"Decision[^\n]*[:：]\s*$", text, re.MULTILINE):
            issues.append(f"{rel}: marked Resolved but missing Decision content")

    return issues


def main() -> int:
    args = sys.argv[1:]
    roots = [REPO / a for a in args] if args else [REPO]
    files = relevant_md_files(roots)
    all_issues: list[str] = []
    for f in files:
        all_issues.extend(lint(f))

    if not all_issues:
        print(f"[ok] scanned {len(files)} file(s), no issues")
        return 0
    for line in all_issues:
        print(line)
    print(f"\n[fail] {len(all_issues)} issue(s) across {len(files)} file(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
