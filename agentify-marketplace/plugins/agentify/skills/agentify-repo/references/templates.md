# Templates

The `<...>` are holes to fill with evidence from the repo. If a hole can't be verified,
write `gap — confirm with <team>` in its place. The templates are the expected shape,
not a straitjacket: you can add sections the repo justifies, but don't remove the ones
already here.

---

## AGENTS.md (repo root)

```markdown
---
type: Repository
app: <nombre-del-artefacto-desplegable>
archetype: <lenguaje>-<estilo>-<naturaleza>
criticality: <low|medium|high|critical>
slack_channel: "<#channel or gap — confirm with <team>>"
on_call: "<team/rotation or gap — confirm with <team>>"
version: <short-git-sha>
validated: <YYYY-MM-DD>
update_when: when the repo identity, reading order, or maintenance rule changes
---

# AGENTS.md

## 1. Security & Environment

- **trigger**: always
- **rule file**: `@docs/agent/security-rules.md`
- **description**: The agent must read the full contents of `security-rules.md` before
  editing code or configuration. It contains the security guidelines, environment
  configuration, and operational restrictions that let it operate safely and in line
  with the project's standards.

## Identity

`<app>` is a **<archetype in prose>** that <what it does, what it consumes, what it produces>.
<What it is NOT and who its only callers are>.

## How to use this package

Read the orientation guide in `docs/agent/` in this order:

1. [overview.md](docs/agent/overview.md) — what this repo does, what capabilities it has, and where each one lives in the code.
2. [architecture.md](docs/agent/architecture.md) — layers, entrypoints, repository map, data flow.
3. [contracts.md](docs/agent/contracts.md) — what it exposes and what it depends on.
4. [runbook.md](docs/agent/runbook.md) — how to build/run/test and the Definition of Done.
5. [traps.md](docs/agent/traps.md) — tacit traps that aren't visible in the code.
6. [rules.md](docs/agent/rules.md) — how acceptable code is written here.
7. [security-rules.md](docs/agent/security-rules.md) — security rules.

## Maintenance

Update `version` and `validated` when the repo's identity, reading order, or maintenance
rule changes. Open `gap —` markers are open questions for the owning team.
```

Notes on the front-matter:
- `version`: `git rev-parse --short HEAD`. It's the snapshot of the repo the package was
  validated against.
- `validated`: today's date in ISO. Lets a future reader know how stale this is.
- `archetype`: use it consistently across repos in the same organization; it's what lets you
  group and compare services later.
- If the organization already has versioned corporate rules (e.g. `.agentic-rules/go/...`),
  point `rule file` there and let `security-rules.md` reference that source.

---

## docs/agent/overview.md

```markdown
# Overview

## What this repo does
<2-4 paragraphs: business purpose, triggers, observable outcome. No marketing.>

## Capabilities
| Capability | What it does | Where it lives |
|---|---|---|
| <name> | <one line> | `<path/to/package>` |

## What it does NOT do
<Explicit boundaries: responsibilities that look like its own but live in another service.>

## Glossary
<Domain terms and internal acronyms the code uses without explaining.>
```

---

## docs/agent/architecture.md

```markdown
# Architecture

## Style
<Architectural style and the evidence that backs it.>

## Repository map
<Tree pruned to 2 levels, each relevant folder with a one-line purpose.
Skip node_modules, vendor, build, and equivalent noise.>

## Layers
| Layer | Path | Responsibility | May import |
|---|---|---|---|

## Entrypoints
| Type | Path / topic / schedule | File | Handler |
|---|---|---|---|

## Main flow
<Numbered, from entry to final effect, naming real files and functions.>

## Wiring and dependencies
<Where the dependency graph is built and how to register something new.>

## State and persistence
<What gets stored, where, with what schema, and who else reads it.>

## Design decisions with consequences
<Non-obvious decisions and what breaks if reverted. Link ADRs if they exist.>
```

---

## docs/agent/contracts.md

```markdown
# Contracts

## Exposes
### <endpoint | topic | event>
- **Interface**: <METHOD /path | topic name | event name>
- **File**: `<path>`
- **Payload**: <key fields and types>
- **Errors**: <codes and meaning>
- **Idempotency / retries**: <actual behavior>
- **Breaks if**: <what change breaks consumers>

## Depends on
### <service | database | queue | cache>
- **What for**: <usage>
- **Client**: `<path>`
- **Timeouts / retries**: <real values or gap>
- **Failure mode**: <degrades | retries | propagates>

## Fragile contracts
<What an agent must not touch without coordinating with another team.>
```

---

## docs/agent/runbook.md

```markdown
# Runbook

## Prerequisites
<Tools and exact versions.>

## Commands
| Goal | Command |
|---|---|
| Install dependencies | `<cmd>` |
| Build | `<cmd>` |
| Run locally | `<cmd>` |
| Tests | `<cmd>` |
| Run a single test | `<cmd>` |
| Lint / format | `<cmd>` |

## Environment variables
| Variable | What for | Where it comes from | Required? |
|---|---|---|---|
<Never include secret values, not even realistic-looking examples.>

## Running with dependencies
<docker-compose, test containers, mocks, or how to point at an environment.>

## Definition of Done
- [ ] <verifiable criterion>
- [ ] <verifiable criterion>

## CI
<What runs in the pipeline, in what order, and what blocks the merge.>
```

---

## docs/agent/traps.md

```markdown
# Traps

Things that can't be deduced by reading the code and that already cost someone time.

## <short title of the trap>
- **Looks like**: <the reasonable assumption>
- **Actually is**: <the reality>
- **What to do**: <concrete action>
- **Evidence**: `<file:line>` or commit `<sha>`
```

---

## docs/agent/rules.md

```markdown
# Code Rules

Rules for writing code in this repository. Derived from the stack and from the
conventions the existing code already follows.

## Repo conventions
<Naming, package organization, test shape, logging style — observed, not invented.>

## Error handling
<The pattern this repo uses, with a short correct and incorrect example.>

## Tests
<What gets tested, how tests are named, what gets mocked, the real coverage threshold.>

## Stack-specific rules
<From references/stacks.md, filtered to what applies here.>

## Automated vs. judgment
<What the linter already checks (don't repeat it in prose) and what depends on the author's judgment.>
```

---

## docs/agent/security-rules.md

```markdown
# Security Rules

- **trigger**: always
- **scope**: every change to code, configuration, or dependencies in this repository

## Origin
<If corporate rules are already versioned somewhere, reference that file. If not, say so explicitly.>

## Rules
### Secrets and credentials
### Untrusted input and validation
### Authentication and authorization
### Sensitive data and logging
### Dependencies and supply chain
### Per-environment configuration

## Absolute prohibitions
<Short list of things the agent never does in this repo, with the reason.>

## When to stop and ask
<Changes that require human review before continuing.>
```
