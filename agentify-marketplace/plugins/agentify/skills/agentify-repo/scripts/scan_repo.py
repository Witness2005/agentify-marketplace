#!/usr/bin/env python3
"""Deterministic inventory of a repository, as input for agentification.

Usage:
    python3 scan_repo.py <repo-path> [--out .agentify/scan.json] [--check]

--check only evaluates the "is this a development project" gate and prints
APPLIES / NOT_APPLICABLE (exit code 0 / 2).

Stdlib only. The output is hypotheses to confirm by reading the code, not ground truth.
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys
from datetime import date

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "target", "out",
    ".venv", "venv", "__pycache__", ".idea", ".vscode", ".next", ".nuxt",
    "bin", "obj", ".gradle", ".mvn", "coverage", ".pytest_cache", ".terraform",
    "Pods", "DerivedData", ".cache", "site-packages",
}

LANG_BY_EXT = {
    ".go": "Go", ".java": "Java", ".kt": "Kotlin", ".scala": "Scala",
    ".py": "Python", ".rb": "Ruby", ".php": "PHP", ".rs": "Rust",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".mjs": "JavaScript", ".cs": "C#", ".cpp": "C++",
    ".cc": "C++", ".c": "C", ".h": "C/C++ header", ".swift": "Swift",
    ".m": "Objective-C", ".ex": "Elixir", ".exs": "Elixir", ".dart": "Dart",
    ".sh": "Shell", ".sql": "SQL", ".tf": "Terraform", ".vue": "Vue",
}

MANIFESTS = {
    "go.mod": "Go", "package.json": "Node", "pom.xml": "Java/Maven",
    "build.gradle": "Java/Gradle", "build.gradle.kts": "Kotlin/Gradle",
    "pyproject.toml": "Python", "requirements.txt": "Python",
    "Pipfile": "Python", "setup.py": "Python", "Cargo.toml": "Rust",
    "Gemfile": "Ruby", "composer.json": "PHP", "mix.exs": "Elixir",
    "pubspec.yaml": "Dart", "CMakeLists.txt": "C/C++", "Package.swift": "Swift",
}

CI_FILES = [
    ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml",
    "azure-pipelines.yml", ".travis.yml", "bitbucket-pipelines.yml", ".drone.yml",
]

PLATFORM_FILES = [
    "fury.json", "catalog-info.yaml", "service.yaml", "app.yaml", "Procfile",
    "manifest.yml", "CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS",
]

CONTAINER_FILES = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore"]

FRAMEWORK_HINTS = {
    "gin-gonic/gin": "Gin (Go HTTP)", "labstack/echo": "Echo (Go HTTP)",
    "gofiber/fiber": "Fiber (Go HTTP)", "gorilla/mux": "Gorilla Mux (Go HTTP)",
    "spring-boot": "Spring Boot", "quarkus": "Quarkus", "micronaut": "Micronaut",
    "express": "Express", "@nestjs/core": "NestJS", "fastify": "Fastify",
    "next": "Next.js", "react": "React", "vue": "Vue", "@angular/core": "Angular",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "sqlalchemy": "SQLAlchemy", "celery": "Celery",
    "rails": "Ruby on Rails", "laravel": "Laravel",
    "actix-web": "Actix Web", "axum": "Axum",
    "kafka": "Kafka", "rabbitmq": "RabbitMQ", "amqp": "AMQP",
    "aws-sdk": "AWS SDK", "grpc": "gRPC", "graphql": "GraphQL",
}

ENTRYPOINT_PATTERNS = [
    (re.compile(r"(^|/)main\.go$"), "Go main"),
    (re.compile(r"(^|/)cmd/[^/]+/main\.go$"), "Go cmd binary"),
    (re.compile(r"(^|/)(index|server|app|main)\.(ts|js|mjs)$"), "Node entrypoint"),
    (re.compile(r"(^|/)(main|app|wsgi|asgi|manage)\.py$"), "Python entrypoint"),
    (re.compile(r".*Application\.(java|kt)$"), "JVM application"),
    (re.compile(r"(^|/)Program\.cs$"), "\u002ENET entrypoint"),
    (re.compile(r"(^|/)src/main\.rs$"), "Rust entrypoint"),
]

LAYER_HINTS = {
    "domain": "domain", "internal/domain": "domain", "core": "core",
    "application": "application", "usecase": "use cases", "usecases": "use cases",
    "service": "services", "services": "services", "handler": "entrypoint",
    "handlers": "entrypoint", "controller": "entrypoint", "controllers": "entrypoint",
    "adapter": "adapters", "adapters": "adapters", "port": "ports",
    "ports": "ports", "infrastructure": "infrastructure", "infra": "infrastructure",
    "repository": "persistence", "repositories": "persistence", "model": "models",
    "models": "models", "entity": "entities", "entities": "entities",
    "api": "api", "cmd": "binaries", "pkg": "public packages",
    "internal": "internal packages", "test": "tests", "tests": "tests",
}

TEST_PATTERNS = [
    re.compile(r"_test\.go$"), re.compile(r"(^|/)test_.*\.py$"),
    re.compile(r".*\.(test|spec)\.(ts|tsx|js|jsx)$"), re.compile(r".*Test\.(java|kt)$"),
    re.compile(r".*Tests\.cs$"), re.compile(r"(^|/)tests?/"), re.compile(r"(^|/)spec/"),
]

ENV_RE = re.compile(
    r"""(?:os\.Getenv\(|process\.env\.|os\.environ\.get\(|os\.environ\[|"""
    r"""System\.getenv\(|Environment\.GetEnvironmentVariable\(|env::var\()"""
    r"""\s*["']?([A-Z][A-Z0-9_]{2,})""",
)

SCANNABLE_EXT = {
    ".go", ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".java", ".kt",
    ".cs", ".rb", ".rs", ".php", ".yml", ".yaml", ".toml",
}


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def walk(root):
    """Returns (relative_paths, level1_dir_map)."""
    files, top = [], collections.Counter()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git")]
        rel_dir = os.path.relpath(dirpath, root)
        for fn in filenames:
            rel = os.path.normpath(os.path.join(rel_dir, fn)).replace("\\", "/")
            if rel.startswith("./"):
                rel = rel[2:]
            files.append(rel)
            top[rel.split("/")[0]] += 1
        if len(files) > 60000:
            break
    return files, top


def read_text(path, limit=400_000):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(limit)
    except Exception:
        return ""


def detect_languages(files):
    counts = collections.Counter()
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        lang = LANG_BY_EXT.get(ext)
        if lang:
            counts[lang] += 1
    total = sum(counts.values()) or 1
    return [
        {"language": lang, "files": n, "share": round(100.0 * n / total, 1)}
        for lang, n in counts.most_common(12)
    ]


def detect_frameworks(root, files):
    blobs = []
    for name in ("go.mod", "package.json", "pom.xml", "build.gradle", "build.gradle.kts",
                 "pyproject.toml", "requirements.txt", "Cargo.toml", "Gemfile", "composer.json"):
        if name in files:
            blobs.append(read_text(os.path.join(root, name), 200_000).lower())
    joined = "\n".join(blobs)
    return sorted({label for key, label in FRAMEWORK_HINTS.items() if key in joined})


def detect_entrypoints(files):
    out = []
    for f in files:
        for pattern, label in ENTRYPOINT_PATTERNS:
            if pattern.search(f):
                out.append({"file": f, "kind": label})
                break
    return out[:40]


def detect_env_vars(root, files):
    found = collections.Counter()
    scanned = 0
    for f in files:
        if os.path.splitext(f)[1].lower() not in SCANNABLE_EXT:
            continue
        if scanned > 1500:
            break
        scanned += 1
        for m in ENV_RE.finditer(read_text(os.path.join(root, f), 120_000)):
            found[m.group(1)] += 1
    return [v for v, _ in found.most_common(60)]


def git_info(root):
    info = {
        "short_sha": run(["git", "rev-parse", "--short", "HEAD"], root),
        "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root),
        "last_commit_date": run(["git", "log", "-1", "--format=%cs"], root),
        "commit_count": run(["git", "rev-list", "--count", "HEAD"], root),
        "remote": run(["git", "config", "--get", "remote.origin.url"], root),
    }
    authors = run(["git", "shortlog", "-sne", "--no-merges", "HEAD"], root)
    info["top_authors"] = [ln.strip() for ln in authors.splitlines()[:8]] if authors else []
    # Only trap-hunter needs commit messages; they go into a separate file
    # (.agentify/commits.json) so the other 5 passes don't pay to read them.
    return info


def recent_commits(root):
    subjects = run(["git", "log", "-80", "--format=%h %s"], root)
    return subjects.splitlines()[:80] if subjects else []


def previous_agentify_run(root, current_sha):
    """If an AGENTS.md from a previous run already exists, computes what changed
    since then. Lets the orchestrator skip passes whose input didn't change."""
    agents_path = os.path.join(root, "AGENTS.md")
    if not os.path.isfile(agents_path) or not current_sha:
        return None
    with open(agents_path, encoding="utf-8", errors="ignore") as fh:
        head = fh.read(4000)
    m = re.search(r"^version:\s*[\"']?([0-9a-f]{4,40})[\"']?\s*$", head, re.M)
    if not m:
        return None
    prev_sha = m.group(1)
    if prev_sha == current_sha:
        return {"previous_sha": prev_sha, "changed_files": [], "unchanged": True, "resolvable": True}
    try:
        r = subprocess.run(["git", "diff", "--name-only", f"{prev_sha}..HEAD"],
                            cwd=root, capture_output=True, text=True, timeout=20)
    except Exception:
        return {"previous_sha": prev_sha, "changed_files": [], "unchanged": False, "resolvable": False}
    if r.returncode != 0:
        # the stored sha no longer exists in history (rebase/squash/another clone):
        # the diff can't be trusted, this must be treated as a full run.
        return {"previous_sha": prev_sha, "changed_files": [], "unchanged": False, "resolvable": False}
    changed = r.stdout.splitlines()
    return {"previous_sha": prev_sha, "changed_files": changed, "unchanged": not changed, "resolvable": True}


def infer_archetype(languages, frameworks, dirs, files):
    lang = languages[0]["language"].lower().replace("#", "sharp").replace("/", "-") if languages else "unknown"
    lang = {"typescript": "node", "javascript": "node", "kotlin": "jvm", "java": "java"}.get(lang, lang)

    dirset = {d.lower() for d in dirs}
    for f in files:
        for seg in f.split("/")[:-1]:
            dirset.add(seg.lower())
    pathblob = "\n".join(files).lower()
    if {"domain", "ports", "adapters"} & dirset or ("internal/domain" in pathblob and "adapter" in pathblob):
        style = "hexagonal"
    elif {"controllers", "models", "views"} <= dirset:
        style = "mvc"
    elif "usecase" in pathblob or "usecases" in pathblob:
        style = "clean"
    elif {"services", "repositories"} & dirset:
        style = "layered"
    else:
        style = "flat"

    fw = " ".join(frameworks).lower()
    if any(k in fw for k in ("kafka", "rabbitmq", "amqp")) or "consumer" in pathblob:
        nature = "service-event-driven"
    elif "graphql" in fw:
        nature = "graphql-api"
    elif "grpc" in fw:
        nature = "grpc-service"
    elif any(k in fw for k in ("react", "vue", "angular", "next.js")):
        nature = "frontend-app"
    elif any(k in fw for k in ("gin", "echo", "fiber", "express", "fastapi", "flask", "spring", "nestjs", "fastify")):
        nature = "rest-api"
    elif any(f.startswith("cmd/") for f in files):
        nature = "cli"
    else:
        nature = "library"
    return f"{lang}-{style}-{nature}"


def applies(root, files):
    reasons = []
    manifests = [m for m in MANIFESTS if m in files]
    if manifests:
        reasons.append(f"manifests: {', '.join(manifests)}")
    code_files = sum(1 for f in files if os.path.splitext(f)[1].lower() in LANG_BY_EXT)
    if code_files >= 5:
        reasons.append(f"{code_files} source code files")
    if any(c in files for c in CONTAINER_FILES):
        reasons.append("container files")
    if any(f.endswith(".tf") or "/templates/" in f and f.endswith(".yaml") for f in files):
        reasons.append("infrastructure as code")
    return (bool(manifests) or code_files >= 5), reasons


def build_report(root):
    files, top = walk(root)
    ok, reasons = applies(root, files)
    languages = detect_languages(files)
    frameworks = detect_frameworks(root, files)
    dirs = [d for d, n in top.most_common(40) if os.path.isdir(os.path.join(root, d))]

    report = {
        "scanned_path": os.path.abspath(root),
        "scanned_on": date.today().isoformat(),
        "is_development_project": ok,
        "gate_reasons": reasons,
        "file_count": len(files),
        "languages": languages,
        "manifests": {m: MANIFESTS[m] for m in MANIFESTS if m in files},
        "frameworks": frameworks,
        "entrypoints": detect_entrypoints(files),
        "top_level_dirs": [
            {"dir": d, "files": top[d], "likely_role": LAYER_HINTS.get(d.lower(), "")}
            for d in dirs
        ],
        "layer_dirs": sorted({
            "/".join(f.split("/")[:-1]) for f in files
            if any(seg.lower() in LAYER_HINTS for seg in f.split("/")[:-1])
        })[:60],
        "test_files": sum(1 for f in files if any(p.search(f) for p in TEST_PATTERNS)),
        "ci": [c for c in CI_FILES if c in files or os.path.exists(os.path.join(root, c))],
        "containers": [c for c in CONTAINER_FILES if c in files],
        "platform_files": [p for p in PLATFORM_FILES if p in files],
        "has_makefile": "Makefile" in files or "makefile" in files,
        "existing_agent_docs": sorted(
            f for f in files
            if f in ("AGENTS.md", "CLAUDE.md", ".cursorrules") or f.startswith("docs/agent/")
        ),
        "docs": sorted(f for f in files if f.lower().startswith("docs/"))[:60],
        "env_vars": detect_env_vars(root, files),
        "git": git_info(root),
    }
    report["proposed_archetype"] = infer_archetype(
        languages, frameworks, [d["dir"] for d in report["top_level_dirs"]], files
    ) if ok else None
    report["previous_agentify_run"] = previous_agentify_run(root, report["git"]["short_sha"])
    return report


def main():
    ap = argparse.ArgumentParser(description="Scans a repo to agentify it")
    ap.add_argument("path", help="repository path")
    ap.add_argument("--out", default=".agentify/scan.json", help="output JSON path")
    ap.add_argument("--check", action="store_true", help="only evaluate the gate")
    args = ap.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 1

    report = build_report(root)

    if args.check:
        if report["is_development_project"]:
            print("APPLIES: " + "; ".join(report["gate_reasons"]))
            return 0
        print("NOT_APPLICABLE: no manifests or enough source code found")
        return 2

    out = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    # Commit messages in a separate file: only trap-hunter needs them, so the
    # other 5 passes don't pay to read them inside scan.json.
    commits_out = os.path.join(os.path.dirname(out), "commits.json")
    with open(commits_out, "w", encoding="utf-8") as fh:
        json.dump({"recent_commits": recent_commits(root)}, fh, indent=2, ensure_ascii=False)

    langs = ", ".join(f"{l['language']} {l['share']}%" for l in report["languages"][:3])
    print(f"Written: {out}")
    print(f"Written: {commits_out} (trap-hunter only)")
    print(f"  development: {report['is_development_project']}")
    print(f"  proposed archetype: {report['proposed_archetype']}")
    print(f"  languages: {langs or 'none'}")
    print(f"  entrypoints: {len(report['entrypoints'])} | tests: {report['test_files']}")
    print(f"  sha: {report['git']['short_sha'] or 'no git'}")
    if report["existing_agent_docs"]:
        print(f"  HEADS UP, agent documentation already exists: {report['existing_agent_docs']}")
    prev = report["previous_agentify_run"]
    if prev and prev["resolvable"]:
        if prev["unchanged"]:
            print("  previous run detected, no changes since then: everything can be skipped")
        else:
            print(f"  previous run detected: {len(prev['changed_files'])} file(s) changed "
                  f"since {prev['previous_sha']} -> evaluate which passes to relaunch")
    elif prev and not prev["resolvable"]:
        print("  previous AGENTS.md references a sha no longer in history: treat as a full run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
