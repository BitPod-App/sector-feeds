# BUG_MONITORING_STACK_V1

Status: DRAFT  
Owner: CJ  
Last updated: 2026-02-28  
Purpose: Choose a Sentry-like monitoring stack without adding recurring spend.

---

## Goal
Capture runtime errors + exceptions with enough context to:
- triage quickly
- reproduce reliably
- link to a Linear bug ticket
- verify fixes

Constraint: avoid new monthly costs unless absolutely necessary.

---

## Option A: Sentry (hosted) — start here if free tier is sufficient

Pros
- Fastest time-to-value
- Strong SDK ecosystem
- Great issue grouping + context

Cons
- Usage/seat limits on free tier
- Another SaaS dependency

When to choose
- You want “works today” and are fine with constraints.

---

## Option B: GlitchTip (self-hosted, Sentry-compatible) — best $0 long-term

Pros
- Self-host control (no SaaS bill)
- Works with Sentry SDKs (drop-in-ish)
- Keeps you portable (instrument once, switch backend later)

Cons
- You run it (deployment, upgrades, backups)
- You need a server/container environment

When to choose
- You want a “Sentry-shaped” backend without paying.

---

## Option C: Minimum viable structured logging (Week 1)

If you’re too early for a full error platform, do this instead:

1) Global exception handler (client) / middleware (server)
2) Structured JSON logs
3) Central log sink (even a file sink + rotation)  
4) Create Linear bugs with:
   - time window
   - request id / session id
   - log excerpt (NO secrets)

Not as good as Sentry, but enough for Week 1.

---

## Integration rules (with Linear)

Rule 1: Every monitoring alert becomes either:
- a Linear bug ticket, or
- a “suppressed / known” entry with rationale

Rule 2: Bug ticket body MUST include:
- top stack trace (short)
- environment + version/build
- repro attempt status
- link to monitoring event

Rule 3: Never paste secrets (tokens/keys/DSNs) into Linear.

---

## Recommendation

Week 1:
- Use Sentry free tier **or** minimum viable logging (zero platform setup).

When you start hitting limits or want control:
- Move to GlitchTip self-host while keeping the same Sentry SDK instrumentation pattern.
