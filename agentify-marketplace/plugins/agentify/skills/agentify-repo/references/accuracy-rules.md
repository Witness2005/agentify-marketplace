# Accuracy rules (mandatory)

Apply to all six passes and to the editor. They are stricter than the "Golden rule: no
invention" from `SKILL.md` — they detail the cases where it's easy to fail without noticing:
inferred flow instead of read flow, controls placed where they "should" be instead of where
they actually are, and claims about security or side effects made without evidence.

1. **Trace, don't infer.** Describe behavior by reading the real code, from the entry point
   (HTTP, CLI, event, job) to persistence and back. Don't rely on names, comments,
   docstrings, or framework conventions. Cite `file:line` at each step of the flow.

2. **Locate each control where it actually happens.** For authentication, authorization,
   validation, and error handling, state which layer it lives in (middleware, decorator,
   handler, service, model). Every section and table in the document must agree — if one
   table says "auth in middleware" and the flow says "auth in the handler", that's a
   contradiction to resolve before delivering, not to let slide.

3. **Explicit security boundaries.** Whenever the document touches security, always document:
   - each entrypoint's auth mechanism and whether it bypasses or replaces the framework's
     native one,
   - the identity and privileges each operation runs with, and every point where permissions
     are elevated or bypassed (sudo, bypass, service account),
   - whether custom controls replace or add to the framework's own (RBAC, middleware),
   - each distinct credential or auth scheme (tokens, API keys, query string, unauthenticated
     public endpoints), named unambiguously — if there are two tokens, name and distinguish
     them.

4. **Exact side effects.** State precisely when logging, auditing, commits, rollbacks,
   retries, or published events occur: always, only on success, or only on error. Note
   whether that behavior differs in tests, and which exception maps to which code or response.

5. **Flag what's misleading.** Report parameters or fields that get parsed but never used,
   implicit default values, and any behavior that would surprise someone reading only the
   signature or existing documentation.

6. **Literal precision.**
   - Entrypoints/routes: one row per exact pattern, without merging distinct variants.
   - Framework mechanisms: verify how they're registered and executed in the code; don't
     assume the "typical" decorator or hook for that framework unless you confirmed it.
   - Counts and lists: must match exactly what the document enumerates.

7. **Label certainty.** Mark every non-obvious claim as **[Verified]** (with a citation),
   **[Inferred]** (with its justification), or as `gap — confirm with <team>` when evidence
   is missing and you can't verify it — that's the gap marker already used throughout the
   package; don't invent a new label for it. Don't present performance, concurrency, or
   design intent as facts without evidence.

8. **Final self-review.** Before writing your definitive output file, reread your own draft
   looking for contradictions between sections, unsupported claims, and omitted security
   details. Fix them there — don't leave them for the editor pass.
