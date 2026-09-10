---
description: Agentifies the current repository (AGENTS.md + docs/agent/) with multi-agent passes, requesting the minimum permissions
argument-hint: "[repo-path] [--dry-run]"
allowed-tools: Read, Glob, Grep, Write, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/agentify-repo/scripts/scan_repo.py:*), Task
---

# /agentify

Goal: produce the agent context package for the repo at `$1` (defaults to the current
directory), following the `agentify-repo` skill, with the least permission and token spend
possible.

## Procedure

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/agentify-repo/SKILL.md` in full and follow it.
2. Scan (the only use of Bash in the whole flow — one single command, not two):
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/agentify-repo/scripts/scan_repo.py "${1:-.}" --out .agentify/scan.json
   ```
   With Read, open `.agentify/scan.json` and check `is_development_project`. If it's `false`,
   answer exactly `not applicable` and stop — don't spend further steps or tokens. Also check
   `previous_agentify_run`: if `unchanged: true`, there's nothing to regenerate — skip to
   step 6 and report that nothing changed since the previous run.
3. If it applies and there are changes, launch in parallel with the Task tool only the
   subagents whose input touches `changed_files` (all of them, if there's no resolvable
   previous run) among `repo-scout`, `architect`, `contract-mapper`, `ops-engineer` and
   `trap-hunter` — see the "Incremental runs" table in `SKILL.md`. All `model: haiku`,
   Read/Glob/Grep/Write only — they don't request Bash; `trap-hunter` reads
   `.agentify/commits.json` for commit messages, not `scan.json`. Pass each one the repo path
   and the `scan.json` path, and explicitly tell it to write its own output file itself with
   Write and reply with a one-line summary, not the full content — that way you don't
   duplicate those documents in your own context. Once `repo-scout` finishes (or is skipped),
   launch `standards-writer` if applicable (same criteria: haiku, no Bash).
4. With the one-line summaries from each subagent (don't re-read the full documents unless
   you need to verify something specific), write `AGENTS.md` and `docs/agent/overview.md`
   yourself.
5. Validate with Read/Glob (no Bash): the 8 files exist, `AGENTS.md`'s front-matter is
   complete, relative links resolve, and no template placeholders are left unfilled. Fix
   whatever is missing.
6. Summarize: files created/regenerated, which were reused unchanged (incremental run), the
   assigned `archetype`, and the `gap —` markers as questions for the owning team.

With `--dry-run`, run through step 3 and show the plan and findings without writing files.
The generated documents are **always written in English**, with no exception and no option
to configure it.

Non-negotiable rule: nothing you write can be invented. What can't be verified is declared
as `gap — confirm with <team>`.
