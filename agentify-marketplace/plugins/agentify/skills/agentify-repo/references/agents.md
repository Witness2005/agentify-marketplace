# Multi-agent passes

Each pass is a role with its own question, a bounded set of files to look at, and a
deliverable. The separation matters because each role hunts different evidence: the one
mapping contracts reads handlers and HTTP clients; the one hunting traps reads git history
and configuration. Mixing them produces generic documents.

Context every pass receives:

```
Repo: <path>
Inventory: .agentify/scan.json
Golden rule: only state what's verifiable. What can't be verified is written as
"gap — confirm with <team>". Don't invent service names, topics, endpoints, or owners.
Accuracy rules: references/accuracy-rules.md (read them before writing your document).
Output: <output-path> (Markdown, no front-matter unless stated)
```

In Claude Code these run as parallel subagents (1-5 together, 6 after 1, editor last).
In Claude.ai you run them yourself in sequence, saving each output before moving to the next.

**Token consumption**: each pass starts from `.agentify/scan.json` instead of rescanning the
tree with Glob from scratch, and only opens with Read the files that Grep/scan already
flagged as relevant — not the whole repo. The six passes (`repo-scout`, `architect`,
`contract-mapper`, `ops-engineer`, `trap-hunter`, `standards-writer`) run on the cheapest
available model (`model: haiku` in each subagent's definition); no role is exempt. Commit
messages (the only thing `trap-hunter` needs) live in `.agentify/commits.json`, separate from
`scan.json`, so the other five passes don't load them. And if `scan.json` carries
`previous_agentify_run` with a bounded set of changes since the last run, don't launch all
six passes from memory — check "Incremental runs" in `SKILL.md` and skip the ones that don't
apply.

---

## 1. repo-scout

**Question**: what is this, who maintains it, and what is it made of?

Look at: manifests, README, `.git`, CODEOWNERS, internal platform files
(`fury.json`, `.mp/`, `service.yaml`, `catalog-info.yaml`), Dockerfile, pipelines.

Produces `.agentify/identity.md` with:
- An identity sentence: what the service is, what it consumes, what it produces, and what it
  is **not** (e.g. "not a public API; its only callers are X").
- `app`: canonical name of the deployable artifact (not the folder name if they differ).
- `archetype`: a composite string `<language>-<architectural-style>-<nature>`,
  e.g. `go-hexagonal-service-event-driven`, `node-express-rest-api`,
  `java-spring-layered-batch`, `python-fastapi-service`. Justify it with evidence
  (`domain/`, `ports/`, `adapters/` folders → hexagonal; queue consumers → event-driven).
- `criticality`: `low` | `medium` | `high` | `critical`. Derive it from evidence, not
  intuition: does it move money?, is it on the critical path of a user flow?, does it have
  replicas and configured alerts?, what do versioned SLOs/alerts say? No evidence →
  `medium` with a gap note.
- `slack_channel` and `on_call`: only if written somewhere in the repo (README,
  catalog-info, CODEOWNERS). If not, `gap — confirm with <team>`.
- Likely owners by commit volume (informative, not authoritative).

---

## 2. architect

**Question**: how is this organized, and where does a request/event come in and go out?

Look at: `main`/`cmd`/`index`/`Application`, dependency wiring, routers, consumers,
cron handlers, layer folders, interfaces and their implementations.

Produces `docs/agent/architecture.md`:
- Repository map: tree pruned to 2 levels, each relevant folder with a one-line purpose,
  skipping `node_modules`, `vendor`, `build`, and equivalent noise. This document is its sole
  owner — don't duplicate it in `overview.md`.
- The real layers with their path in the tree, not the textbook layers.
- Entrypoints table: type (HTTP / queue / cron / CLI), path or topic, file, handler.
- End-to-end data flow for the main case: input → validation → domain → outbound ports →
  effects. Name concrete files and functions.
- A Mermaid diagram only if it clarifies something prose doesn't; if it's decorative, omit it.
- Where wiring happens and how dependencies are injected (what an agent needs to know where
  to register something new).

---

## 3. contract-mapper

**Question**: what does it promise to others, and what does it need from others?

Look at: route definitions, OpenAPI/proto/Avro specs, DTOs, HTTP/gRPC clients,
database repositories, publishers, topic configuration, feature flags.

Produces `docs/agent/contracts.md`, in two halves:
- **Exposes**: every endpoint / consumed topic / published event, with method+path or topic
  name, payload shape (key fields, not the full schema if it's long), its own error codes,
  and retry/idempotency semantics.
- **Depends on**: every external service, database, cache, or queue, with what it's used for,
  where the client lives, timeouts, and what happens on failure (degrades, retries,
  propagates).
- Flags the contracts that break compatibility if touched. It's the information that
  prevents an agent's worst possible mistake.

---

## 4. ops-engineer

**Question**: how do I build it, run it, test it, and how do I know I'm done?

Look at: Makefile/npm scripts/gradle tasks, README, CI, Dockerfile, docker-compose,
test configuration, linters, coverage thresholds, pre-commit hooks.

Produces `docs/agent/runbook.md`:
- Prerequisites with exact versions if pinned (`.tool-versions`, `go.mod`, `engines`).
- Copyable commands for: install, build, run locally, run tests, lint, format. Only commands
  that actually exist; verify the Makefile target is really defined.
- Required environment variables and where they come from (don't include real secret
  values).
- How to run a subset of tests — an agent almost never wants the full suite.
- **Definition of Done**: an actionable checklist for calling a change complete (tests
  passing, lint clean, coverage above the repo's real threshold, contract docs updated if a
  contract changed, changelog/version if the repo uses one).

---

## 5. trap-hunter

**Question**: what would trip up a competent person who only read the code?

This is the most valuable document and the easiest one to ruin with filler. Prefer three
real traps over ten generic ones. "Write tests" is not a trap; "integration tests need the
Postgres container up or they fail with a misleading connection error" is.

Look at: `.agentify/commits.json` (revert, hotfix, "fix flaky", "temporary" — no Bash, don't
run `git log` yourself), TODO/HACK/XXX comments, environment-based conditionals, mocks and
fixtures, edge cases in tests, apparent dead code, names that don't mean what they seem to,
implicit coupling between distant files.

Produces `docs/agent/traps.md`: each trap with what it looks like, what it actually is, and
what to do. If you truly find no traps, say so — it's an honest and useful answer.

---

## 6. standards-writer

**Question**: how is acceptable code written *here*?

Read `references/stacks.md` for the per-technology baseline, but what matters is what's
specific to the repo: extract the conventions by observing the existing code (naming, error
handling, test structure, logging) and the already-versioned linter configuration. A rule
that contradicts 90% of the repo's code is a wrong rule.

Also read `references/conventions-rules.md` before writing: don't state a rule the shown
example doesn't back up, don't reconstruct "expected" examples from memory, don't turn an
observed bug into a standard, require proof for "always"/"never", confirm with Glob which
linters exist (don't assume), state where each type of new code goes, and make sure each
section's heading matches its content.

Produces two files:
- `docs/agent/rules.md` — good coding practices, with a short expected-vs-avoided example
  when it helps. Verifiable rules, not aspirations.
- `docs/agent/security-rules.md` — security rules. If the repo already has a corporate
  security rules folder (e.g. `.agentic-rules/`), this file references that source instead
  of duplicating it, and adds only what's specific to the repo.

---

## 7. editor (you do this one, at the end)

**Question**: does this read as a single, coherent, and true document?

- Write `docs/agent/overview.md` from the identity and capabilities found: what the repo
  does, what capabilities it has, and where each one lives in the code.
- Write `AGENTS.md` with the front-matter and reading order (template in `templates.md`).
- Remove duplication between documents: each fact lives in exactly one file and the others
  link to it.
- Unify the language: all documents are **always written in English**, with no exception
  and no way to configure it — there's no flag or alternative language.
- Run `scripts/validate_agentification.py` and fix whatever it reports.
