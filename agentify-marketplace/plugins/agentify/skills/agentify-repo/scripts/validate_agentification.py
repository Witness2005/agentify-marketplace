#!/usr/bin/env python3
"""Validates the agentification package generated in a repository.

Usage:
    python3 validate_agentification.py <repo-path> [--json]

Checks structure, front-matter, links, unfilled template placeholders,
and suspiciously empty content. Exits with 1 if there are errors, 0 if only warnings.
"""

import argparse
import json
import os
import re
import subprocess
import sys

REQUIRED_DOCS = [
    "overview.md", "architecture.md", "contracts.md",
    "runbook.md", "traps.md", "rules.md", "security-rules.md",
]

REQUIRED_KEYS = [
    "type", "app", "archetype", "criticality",
    "slack_channel", "on_call", "version", "validated", "update_when",
]

VALID_CRITICALITY = {"low", "medium", "high", "critical"}

PLACEHOLDER_RE = re.compile(r"<[a-z][^>\n]{2,60}>|LOREM|TODO_FILL|XXX_FILL|\{\{[^}]+\}\}", re.I)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
GAP_RE = re.compile(r"gap\s+[—-]\s*confirm", re.I)
MIN_LINES = 15
MAX_LINES = 200


def parse_front_matter(text):
    if not text.startswith("---"):
        return None, "AGENTS.md does not start with YAML front-matter (---)"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "front-matter has no closing (---)"
    fm = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, None


def git_short_sha(root):
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def validate(root):
    errors, warnings, info = [], [], []

    agents_path = os.path.join(root, "AGENTS.md")
    if not os.path.isfile(agents_path):
        errors.append("AGENTS.md is missing from the repo root")
        return errors, warnings, info

    with open(agents_path, encoding="utf-8", errors="ignore") as fh:
        agents = fh.read()

    fm, fm_err = parse_front_matter(agents)
    if fm_err:
        errors.append(fm_err)
        fm = {}

    for key in REQUIRED_KEYS:
        if key not in fm:
            errors.append(f"front-matter: missing key '{key}'")
        elif not fm[key]:
            errors.append(f"front-matter: '{key}' is empty")

    if fm.get("criticality") and fm["criticality"] not in VALID_CRITICALITY:
        errors.append(
            f"front-matter: criticality '{fm['criticality']}' is not one of {sorted(VALID_CRITICALITY)}"
        )

    if fm.get("validated") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["validated"]):
        errors.append(f"front-matter: validated '{fm['validated']}' is not an ISO date (YYYY-MM-DD)")

    sha = git_short_sha(root)
    if sha and fm.get("version") and not (
        fm["version"].startswith(sha) or sha.startswith(fm["version"])
    ):
        warnings.append(
            f"front-matter: version '{fm['version']}' does not match current HEAD '{sha}'"
        )

    for section in ("# AGENTS.md", "## Identity", "## How to use this package"):
        if section not in agents:
            warnings.append(f"AGENTS.md: missing section '{section}'")

    docs_dir = os.path.join(root, "docs", "agent")
    if not os.path.isdir(docs_dir):
        errors.append("docs/agent/ directory is missing")
    else:
        for doc in REQUIRED_DOCS:
            path = os.path.join(docs_dir, doc)
            if not os.path.isfile(path):
                errors.append(f"missing docs/agent/{doc}")
                continue
            with open(path, encoding="utf-8", errors="ignore") as fh:
                body = fh.read()
            lines = [ln for ln in body.splitlines() if ln.strip()]
            if len(lines) < MIN_LINES:
                warnings.append(
                    f"docs/agent/{doc}: only {len(lines)} lines with content; looks incomplete"
                )
            elif len(lines) > MAX_LINES:
                warnings.append(
                    f"docs/agent/{doc}: {len(lines)} lines with content, over the {MAX_LINES}-line "
                    "budget; it probably includes detail an agent can read directly from the "
                    "code (pasted code, full schema, etc.) - trim it"
                )
            for m in set(PLACEHOLDER_RE.findall(body)):
                if not GAP_RE.search(m):
                    warnings.append(f"docs/agent/{doc}: unfilled template placeholder: {m}")

    for link in LINK_RE.findall(agents):
        if link.startswith(("http://", "https://", "#", "mailto:", "@")):
            continue
        target = os.path.join(root, link.split("#")[0])
        if not os.path.exists(target):
            errors.append(f"AGENTS.md: broken link -> {link}")

    gaps = []
    for rel in ["AGENTS.md"] + [f"docs/agent/{d}" for d in REQUIRED_DOCS]:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                if GAP_RE.search(line):
                    gaps.append(f"{rel}:{i}: {line.strip()[:110]}")

    if gaps:
        info.append(f"{len(gaps)} gap(s) pending confirmation with the team:")
        info.extend("  " + g for g in gaps[:25])
        if len(gaps) > 25:
            info.append(f"  ... and {len(gaps) - 25} more")
    else:
        info.append("no gaps declared (verify it's because everything was confirmed, not because it was papered over)")

    return errors, warnings, info


def main():
    ap = argparse.ArgumentParser(description="Validates the agentification package")
    ap.add_argument("path", help="repository path")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 1

    errors, warnings, info = validate(root)

    if args.json:
        print(json.dumps(
            {"errors": errors, "warnings": warnings, "info": info, "ok": not errors},
            indent=2, ensure_ascii=False,
        ))
        return 1 if errors else 0

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print("  x " + e)
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print("  ! " + w)
    if info:
        print()
        for i in info:
            print("  - " + i)

    print("\nRESULT:", "FAIL" if errors else ("OK with warnings" if warnings else "OK"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
