---
name: agentify-repo
description: Agentifies a software repository by generating an AGENTS.md with identity front-matter and a docs/agent/ folder with overview, architecture, contracts, runbook, traps, rules, and security-rules. Use it whenever the user asks to "agentify", "agentification", "generate AGENTS.md", "document the repo for agents", "docs/agent", "onboarding for Claude/Cursor/Copilot on this project", or when they ask for persistent context for an agent to work on a repository — even if they don't say the word "skill" or "AGENTS.md". If the analyzed directory is not a software development project, answer exactly "not applicable" and generate no files.
---

# Agentify Repo

Turns a repository into a context package that another agent can read to work safely on the
code: a root `AGENTS.md` (identity + reading order) and seven documents in `docs/agent/`.

The value of this deliverable is in being **verifiable**, not in looking complete. A made-up
document is worse than a declared hole: the agent that reads it later will act on false
information. That's why the rule below is the central one.

## Golden rule: no invention

Everything you write must be traceable to a file in the repo, to a command's output, or to
something the user explicitly told you. When you can't verify something:

```
gap — confirm with <team/owner>
```

That marker is a valid deliverable. Filling the hole with a plausible guess is not. When
you're done, report how many `gap —` markers are left: that's the list of questions for the
team.

## Never delegate a reference read to a generic agent

`accuracy-rules.md`, `conventions-rules.md`, `stacks.md`, and `templates.md` live under
`${CLAUDE_PLUGIN_ROOT}/skills/agentify-repo/references/`, **outside** the working directory
of the repo you're agentifying. Reading them is a single Read call — it never warrants
launching a subagent. If you still need to delegate it (for example within another pass), do
it with one of this plugin's `agentify:*` subagents, never with a `general-purpose` one: a
generic agent can end up sandboxed to the target repo's working directory and lacks
permission to read outside it — the attempt fails, contributes nothing, and relaunching with
the right agent doubles the cost. You (the orchestrator) and the `agentify:*` subagents
already receive `${CLAUDE_PLUGIN_ROOT}` resolved; use Read directly.

## Step 0 — "Does it apply?" gate

Before generating anything, verify the target is a software development project.

It counts as a development project if **at least one** of these signals is present: a
dependency manifest (`go.mod`, `package.json`, `pom.xml`, `build.gradle*`,
`pyproject.toml`, `requirements.txt`, `Cargo.toml`, `Gemfile`, `composer.json`, `*.csproj`),
a non-trivial volume of compilable/executable source code, a `Dockerfile`/deployment
manifests alongside sources, or versioned IaC (`*.tf`, Helm charts).

It does NOT count: folders with only office documents, loose datasets, personal notes,
design material without code, or an empty directory.

If it doesn't apply, answer exactly this and stop — no files created, no suggestions:

```
not applicable
```

If there's reasonable doubt (for example, a repo that's almost all Markdown but with build
scripts), ask the user once before deciding; don't guess silently.

## Step 1 — Deterministic scan (only use of Bash)

Run the scanner **exactly once** — don't call it twice (once with `--check` and once
without); the Step 0 gate is resolved by reading the same result, so Bash permission is
requested only once in the entire flow:

```bash
python3 scripts/scan_repo.py <repo-path> --out .agentify/scan.json
```

Read the generated JSON (with Read, not another command) and check `is_development_project`.
If it's `false`, answer `not applicable` and stop. If it's `true`, the same report carries
`languages`, `manifests`, `frameworks`, `entrypoints`, `layer_dirs`, `top_level_dirs`, CI/CD,
containers, environment variables, and git metadata (sha, authors) — treat it as a hypothesis
to confirm, not as ground truth, but don't rescan the whole tree to get what's already there.
The last 80 commit messages are **not** in `scan.json` — the scanner writes them separately
to `.agentify/commits.json` because only `trap-hunter` needs them; don't pass them (or their
path) to the other five passes.

The same scan carries `previous_agentify_run`: if the repo already has an `AGENTS.md` with
`version: <sha>` in its front-matter, it says whether that sha matches the current HEAD
(`unchanged: true` → nothing changed, all of Step 2 can be skipped) or, if it doesn't match,
the list of `changed_files` since then (`resolvable: true`) to decide which passes to
relaunch. If `resolvable: false`, the stored sha no longer exists in history (rebase, squash,
another clone) — don't trust the diff, treat it as a full run. See "Incremental runs" below
before launching Step 2.

## Step 2 — Multi-agent passes (no Bash, cheap model)

The work is split into six specialized passes, each a subagent with `model: haiku` and only
`Read, Glob, Grep, Write` (no Bash — they don't need a shell because `scan.json` already
carries what used to require a command, so no subagent triggers an extra permission). Launch
them with the Task tool, in parallel except for the last one. The full instructions for each
role are in `references/agents.md`.

| # | Pass | Produces | Input |
|---|------|----------|-------|
| 1 | `repo-scout` | confirmed inventory, identity, `archetype` | `scan.json` + repo |
| 2 | `architect` | `architecture.md` | layers, entrypoints, flow |
| 3 | `contract-mapper` | `contracts.md` | handlers, clients, topics, schemas |
| 4 | `ops-engineer` | `runbook.md` | Makefile, CI, Docker, tests |
| 5 | `trap-hunter` | `traps.md` | `.agentify/commits.json`, TODOs, fragile config |
| 6 | `standards-writer` | `rules.md`, `security-rules.md` | stack + real repo conventions |

### Incremental runs

If `previous_agentify_run.unchanged` is `true`, don't launch anything from Step 2: report in
Step 5 that nothing changed since the previous run and stop.

If it carries `changed_files` (and `resolvable: true`), each pass only warrants relaunching
if some `changed_files` entry falls within what that pass looks at:

| Pass | Relaunch if `changed_files` touches... |
|---|---|
| `repo-scout` | manifests, README, CODEOWNERS, internal platform files |
| `architect` | `main`/`cmd`/`index`, wiring/DI, routers, layer folders |
| `contract-mapper` | routes, OpenAPI/proto specs, DTOs, HTTP/gRPC clients, topic config |
| `ops-engineer` | Makefile, CI, Dockerfile, docker-compose, test/lint config |
| `trap-hunter` | relaunch it whenever there are `changed_files` — it's the cheapest pass (it doesn't re-read code, only `commits.json` + specific spots) and new commits are exactly its input |
| `standards-writer` | source code files (not just config) |

A skipped pass leaves its existing file untouched — it stays as-is on disk. In Step 5, list
explicitly which were relaunched and which were reused unchanged; you don't need to read the
full content of a reused doc, just confirm with Glob that it still exists. If you're unsure
whether a change affects a pass, relaunch it — a cheap rerun beats a lying doc. If
`resolvable: false` or there's no `previous_agentify_run`, run all six.

Each subagent first reads `references/accuracy-rules.md` — the 8 mandatory accuracy rules
(trace the real flow without inferring, locate each control in its real layer, explicit
security boundaries, exact side effects, literal precision, certainty labeling, and
self-review) that govern how each document is written, not just what it contains.

Each subagent writes its own file with Write and replies with a **one-line** summary (not
the full content) — that way the content isn't duplicated in your context and doesn't waste
extra tokens. You yourself close with the **editor** pass: with those summaries (re-read a
full doc only if something doesn't add up), write `AGENTS.md` and `overview.md`, unify the
tone, and validate.

Parallelism rule: passes 1–5 don't read each other, so they can run together. Pass 6 needs
pass 1's inventory. The editor needs everything.

## Step 3 — Writing

The exact templates for the eight files are in `references/templates.md`. The per-stack
criteria (Go, Node/TS, Java, Python, .NET) for `rules.md` and `security-rules.md` are in
`references/stacks.md`.

Final structure:

```
AGENTS.md
docs/agent/
├── overview.md         what the repo does, its capabilities, and where each one lives
├── architecture.md     layers, entrypoints, repository map, data flow
├── contracts.md        what it exposes and what it depends on
├── runbook.md          build/run/test and Definition of Done
├── traps.md            tacit traps that aren't visible in the code
├── rules.md            good coding practices for this stack
└── security-rules.md   security rules
```

Size calibration: `AGENTS.md` short (identity + reading order, ~40-60 lines). Each doc in
`docs/agent/` between 60 and 200 lines — it's a hard budget, not a suggestion;
`architecture.md`, `contracts.md`, and `security-rules.md` are the ones that tend to bloat
because they tempt you to paste full code, specs, or schemas. The rule to stay within budget:
cite `file:line` or the type/function name instead of pasting the block; summarize a
payload's shape in one line of key fields, not the whole DTO; use tables instead of repeated
prose. If a doc is over 200 lines when you finish writing it, that's the signal you included
what the reading agent can open directly in the code — trim it before calling it done, don't
leave it for a later review that won't happen.

If the repo already has `AGENTS.md`, `CLAUDE.md`, or `docs/agent/`, don't overwrite blindly:
read what exists, propose a diff, and keep what's still true.

## Step 4 — Validation

Check it yourself with Read/Glob (no second Bash script): the 8 files exist, `AGENTS.md`'s
front-matter carries the required keys, `AGENTS.md`'s relative links resolve, no template
placeholders were left unfilled, every doc in `docs/agent/` is within the 200-line budget
(if not, ask the owning pass to trim it before closing, don't let it slide), and count the
pending `gap —` markers. Fix whatever is missing. If you prefer the automated check,
`scripts/validate_agentification.py` is still available (it also warns if a doc is over
budget), but it's a second Bash permission the standard flow avoids.

## Step 5 — Delivery

Close with a brief summary: files created, assigned `archetype`, and the list of `gap —`
markers as concrete questions for the repo's owning team. Don't paste the full content of the
documents in the chat; the user already has them on disk.

## Reference files

- `references/agents.md` — role, inputs, outputs, and prompt for each pass. Read it in Step 2.
- `references/accuracy-rules.md` — the 8 mandatory accuracy rules that govern how each pass
  writes. Every subagent reads it before writing its file (Step 2).
- `references/conventions-rules.md` — 7 rules specific to `rules.md` and
  `security-rules.md` (don't state a rule the repo itself doesn't follow). `standards-writer`
  reads it in addition to `accuracy-rules.md`.
- `references/templates.md` — exact templates for the 8 files. Read it in Step 3.
- `references/stacks.md` — code and security rules per technology. Read it when writing
  `rules.md` and `security-rules.md`.
