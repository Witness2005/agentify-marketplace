# Guide per stack

Baseline for `rules.md` and `security-rules.md`. It's a starting point, not the result:
filter it down to what applies to the repo and add what the code already practices. A rule
that 90% of the repo violates isn't a rule, it's a refactor proposal — and belongs in another
document.

## Cross-cutting (every stack)

**Code**
- Errors: propagate with context, don't swallow them; an empty `catch` is a pending bug.
- Boundaries: validate at the edge (handler/consumer), trust the inside. Document where the
  edge is.
- Concurrency: every async job needs explicit cancellation and timeout.
- Configuration: per environment, never hardcoded; fail at startup if something required is
  missing.
- Tests: one per behavior, not per method. Name that describes the case, not the function.
- New dependencies: justify them; each one is attack surface and maintenance surface.

**Security**
- Zero secrets in the repo, including tests and fixtures. If one shows up, it gets rotated,
  not deleted.
- Never log PII, tokens, auth headers, or full request bodies.
- External input always validated and with a maximum size.
- Parameterized queries always; concatenating SQL is an absolute prohibition.
- TLS for all outbound traffic; never disable certificate verification, not even in dev.
- Pinned and audited dependencies; no installing from arbitrary branches or URLs.

---

## Go
- Errors with `fmt.Errorf("...: %w", err)`; `errors.Is/As` to classify. No `panic` in the
  request path.
- `context.Context` as the first parameter, propagated down to the network or DB call.
- Interfaces defined by the consumer, not the producer — this is what makes the hexagonal
  style possible when the repo uses it.
- Table-driven tests with subtests; `t.Parallel()` when there's no shared state.
- Close what you open with `defer` and check `Close`'s error when it matters.
- Security: `crypto/rand` for unpredictable values, never `math/rand`; `html/template` for
  HTML; be careful with `exec.Command` built from external input.
- Typical linters: `golangci-lint`, `go vet`, `gosec`.

## Node / TypeScript
- Strict TypeScript mode; `any` requires a comment justifying it.
- Promises always awaited or handled; no floating promises.
- Input validation with a schema (zod/joi/class-validator) at the HTTP edge.
- No logic in the handler: the handler orchestrates, the service decides.
- Security: `helmet` and explicit CORS on HTTP services; never `eval` or `child_process`
  with user input; `npm audit` in CI; watch for prototype pollution when merging objects.
- Linters: ESLint + Prettier; `tsc --noEmit` in CI.

## Java / Kotlin (Spring)
- Constructor injection, not field injection; it makes testing easier and dependencies
  explicit.
- Own domain exceptions, translated to HTTP in a `@ControllerAdvice`.
- DTOs separate from persistence entities; don't expose the data model.
- Explicit transaction boundaries; watch out for `@Transactional` on private methods.
- Security: Spring Security with explicit per-route rules; named-parameter queries; disable
  external entity processing in XML parsers.
- Linters: Checkstyle/ktlint, SpotBugs, OWASP Dependency-Check.

## Python
- Type hints on public functions; `mypy`/`pyright` in CI if the repo already has it.
- Pinned environments and dependencies (`poetry.lock`, `requirements.txt` with hashes).
- Pydantic validation at the edge for FastAPI services.
- No module-level mutable state; it complicates tests and worker deployments.
- Security: `yaml.safe_load`, never `pickle` on external data; `subprocess` without
  `shell=True`; `secrets` instead of `random` for tokens.
- Linters: `ruff`/`flake8`, `black`, `bandit`.

## .NET / C#
- `async/await` end to end; no `.Result` or `.Wait()` in request paths.
- `IOptions<T>` for configuration; `HttpClientFactory` for HTTP clients.
- Nullable reference types enabled.
- Security: EF Core with parameterized queries; `DataProtection` for sensitive data;
  policy-based authorization, not scattered checks.
- Analyzers: Roslyn analyzers, `dotnet list package --vulnerable` in CI.

---

## Adjustment by archetype

- **event-driven**: idempotency is rule number one; document the deduplication key and what
  happens with out-of-order or reprocessed events.
- **public REST**: versioning, backward-compatible contract, rate limiting, and a uniform
  error schema.
- **batch/cron**: resumability, execution window, and what happens if two runs overlap.
- **library**: the public surface is the contract; everything else must be internal.
