# V1 Audit Report

Audit date: 2026-07-21

## Scope inspected

- Application modules: `main.py`, `db.py`, `calculations.py`, `services.py`, `stripe_billing.py`, `emailing.py`.
- All Jinja templates and static PWA assets.
- All automated test files and fixtures.
- Docker, Render, environment, dependency, README, and security configuration.

## Strengths retained

- Workbook-parity calculation tests and distinct seven-model compensation math.
- Owner distribution in addition to owner-operated load pay.
- Organization-scoped records and empty signup workspace.
- Stripe-hosted Checkout, signed/idempotent webhooks, subscription entitlements, and live-mode safety checks.
- Secure sessions, CSRF, password hashing, reset-token lifecycle, security headers, and throttles.
- Editable/voidable operating records with retained audit history.
- Persistent disk and verified logical SQLite backups.

## Phase 1 gaps closed

- Persisted pre-book offers and negotiation stages.
- Corrected workflow beginning before RateCon.
- Quote versioning and immutable booked snapshots.
- Driver-location source and freshness metadata.
- Deterministic decision reasons and company-specific thresholds.
- Exactly-once opportunity-to-load conversion.

## Open findings

- No commercial routing, market rate, live GPS, ELD, or HOS provider is connected.
- No document upload/private object storage exists; therefore RateCon processing remains deferred.
- Authorization is organization-admin oriented rather than a complete role matrix.
- SQLite and in-process schedulers are single-replica constraints.
- `main.py` remains large and should be split into routers before Phase 2 expands it.
- An independent security review, legal review, and backup-restore drill remain launch-owner actions.

