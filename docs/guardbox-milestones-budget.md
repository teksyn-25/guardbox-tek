# GuardBox — Milestone & Budget Breakdown

**Requested: €40,000 · 80 person-days @ €500/day · 4 milestones.** Each milestone is a concrete, independently verifiable deliverable (NLnet pays per completed milestone).

## M1 — Sandbox hardening — €10,000 *(security engineering, 20 days)*

**Deliverable:** a tested, rigorous isolation baseline.

**Sub-tasks:** default-deny seccomp **allowlist** (empirically traced across all CDR code paths); AppArmor profile; ephemeral per-file isolation (disposable, network-none container per job); published threat model.

**Acceptance criteria:** seccomp `defaultAction: deny` with CI tests asserting the allowlist *and* that JPEG/PNG/WebP decoding still works; AppArmor profile loads; each CDR job demonstrably runs in a fresh, network-less, destroyed-after container; threat model published in-repo.

## M2 — Memory-safe CDR core (Rust) — €14,000 *(backend/Rust development, 28 days)*

**Deliverable:** the parser rewritten in Rust, removing the memory-corruption bug class.

**Sub-tasks:** Rust decode→strip→re-encode for JPEG/PNG/WebP; PyO3 binding; byte-parity test suite against the current libvips engine.

**Acceptance criteria:** Rust core callable from the service via PyO3; parity tests pass (identical inputs → equivalent clean outputs); fuzz/regression corpus runs with no memory-safety errors.

## M3 — Micro-VM isolation prototype — €8,000 *(infrastructure/security, 16 days)*

**Deliverable:** hardware-virtualised per-file containment prototype.

**Sub-tasks:** run a CDR job inside a Firecracker/Kata micro-VM; measure latency and overhead versus the container path.

**Acceptance criteria:** working prototype processes a file end-to-end inside a micro-VM; benchmark report (latency, memory, boot time) published.

## M4 — Secure intake hardening — €8,000 *(mobile + frontend, 16 days)*

**Deliverable:** intake-side gaps closed on mobile and web.

**Sub-tasks:** mobile share-sheet handler that streams bytes to the backend without ever writing the original to app storage; hardened web-viewer containment; end-to-end test suite; security documentation.

**Acceptance criteria:** share handler shown (via instrumentation) never to persist the original; viewer containment documented; E2E tests pass in CI.

## Summary

| Milestone | Days | € |
|---|---|---|
| M1 Sandbox hardening | 20 | 10,000 |
| M2 Rust CDR core | 28 | 14,000 |
| M3 Micro-VM prototype | 16 | 8,000 |
| M4 Intake hardening | 16 | 8,000 |
| **Total** | **80** | **40,000** |

**Rate:** €500/day, made explicit per NLnet guidance.

**Independent security audit:** not budgeted — we request it through NLnet's grantee support services (e.g. NGI Zero Review), keeping this proposal lean.

**Other funding:** none past or present; a planned community crowdfunding campaign funds general development and outreach only — not these milestones (no double funding).

**License:** all outputs AGPL-3.0.
