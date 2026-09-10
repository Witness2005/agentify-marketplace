# agentify

Turns a repository into a context package for agents: an `AGENTS.md` at the root
and seven documents in `docs/agent/`.

## What it generates

```
AGENTS.md                   identity + reading order (front-matter with app, archetype,
                            criticality, slack_channel, on_call, version, validated)
docs/agent/
├── overview.md             what the repo does, its capabilities, and where each one lives
├── architecture.md         layers, entrypoints, repository map, data flow
├── contracts.md            what it exposes and what it depends on
├── runbook.md              build/run/test and Definition of Done
├── traps.md                tacit traps that aren't visible in the code
├── rules.md                good coding practices for this stack
└── security-rules.md       security rules
```

If the analyzed directory is not a development project, it answers `not applicable` and writes
nothing.

## Installation

### As a Claude Code plugin (recommended: uses parallel subagents)

Plugins aren't installed by copying folders: they're installed from a *marketplace*, which
can be a local path. This repo already is one. From the directory that contains
`agentify-marketplace`, open Claude Code and run:

```
/plugin marketplace add ./agentify-marketplace
/plugin install agentify@agentify-local
```

If the install summary says `Run /reload-plugins to activate.`, run that command.

Usage: `/agentify:agentify [path] [--dry-run]`

The generated documents are always written in English. There is no flag or way to request
another language — it's a fixed decision of the plugin, not a configurable option.

For a team, push `agentify-marketplace/` to a git repo and have everyone run
`/plugin marketplace add <org>/<repo>` followed by `/plugin install agentify@agentify-local`.

### As a standalone skill

Copy `skills/agentify-repo/` to `~/.claude/skills/agentify-repo/` (or upload it from the
`.skill` file on Claude.ai). It activates on its own when you ask to agentify a repo. Without
subagents, the passes run in sequence.

## How it works

1. **Gate**: `scan_repo.py --check` decides whether it applies.
2. **Deterministic scan**: `scan_repo.py` produces `.agentify/scan.json` with languages,
   manifests, frameworks, entrypoints, layers, CI, environment variables, and git metadata.
3. **Six specialized passes** (`agents/`): repo-scout, architect, contract-mapper,
   ops-engineer, trap-hunter, standards-writer. The first five run in parallel.
4. **Final edit**: `AGENTS.md` and `overview.md` are written, which depend on the rest.
5. **Validation**: `validate_agentification.py` checks structure, front-matter, links,
   `version` matching the git HEAD, and unfilled template placeholders.

## The rule that holds everything up

Nothing is invented. What can't be verified in the repo is written as
`gap — confirm with <team>`. In the end, those gaps become the list of questions for the
owning team.

## Customization

- `skills/agentify-repo/references/templates.md` — the shape of the 8 files.
- `skills/agentify-repo/references/stacks.md` — rules per technology. This is where you
  wire in your organization's standards (e.g. `.agentic-rules/`).
- `skills/agentify-repo/references/agents.md` — what each pass looks for.
