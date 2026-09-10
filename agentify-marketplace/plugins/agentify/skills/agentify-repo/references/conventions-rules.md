# Rules for convention documents

Apply only to `standards-writer`, when writing `docs/agent/rules.md` and
`docs/agent/security-rules.md`. They are more specific than `accuracy-rules.md` (which also
applies here): while those cover accuracy in general, these cover the typical mistake of a
convention document — stating a plausible rule that the repo itself doesn't follow.

1. **Rule = example.** The pattern you state must literally describe the examples you show.
   If, while citing the example, you notice it doesn't match the rule, fix the rule or drop
   the example — never leave both if they contradict each other.
2. **"Expected" is copied, not reconstructed.** Examples of what's expected are real
   fragments from the repo, with `file:line`, complete and syntactically valid — don't
   rewrite them "cleaner" from memory. Mark "Avoid" examples that didn't come from the repo
   (illustrating an antipattern the repo avoids, not one it committed) explicitly as
   illustrative, so they don't pass as evidence.
3. **Don't canonize bugs.** If a pattern you observed across several files looks incorrect in
   itself (a mistyped exception, `print` instead of the project's logger), don't document it
   as the standard to follow — report it as a finding (in `traps.md` if applicable, or as a
   separate note) and document the correct pattern if one exists, or the gap if it doesn't.
4. **Absolutes need proof.** "All", "always", or "never" are only written if you genuinely
   reviewed every relevant case (not a sample). If not, use "observed in N of M files
   reviewed" or label the claim as **[Inferred]**.
5. **Confirm the absence of tools, don't assume it.** Search with Glob for
   linter/formatter/type-checker configuration files (`.eslintrc*`, `.golangci.yml`,
   `pyproject.toml` with `[tool.ruff]`/`[tool.black]`, `.editorconfig`, etc.), name them, and
   state explicitly which exist and which don't — "no linter configured" is as valid a claim
   as "uses golangci-lint with the config in `.golangci.yml`", but it must be based on having
   searched, not on its absence from `scan.json`.
6. **Include the "where".** Beyond how code is written, state which layer, folder, or file
   each type of new code should go in (a new use case goes in `<path>`, a new DTO in
   `<path>`) — without this the rule isn't actionable for whoever is going to write the code.
7. **Coherent headings.** Labels and headings (`[Automated]`, "Automated Checks",
   `trigger: always`) must match the section's actual content — if a section is titled
   "Automated Checks" but describes a convention no linter enforces, fix the title or move
   the content to the right section.
