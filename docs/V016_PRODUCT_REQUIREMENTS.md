# CarrierOS v0.16 Product Requirements

Status: architecture baseline; implementation is split across four reviewable pull requests.

## Product outcome

CarrierOS must let a carrier decide whether a broker/customer offer makes money **before** a RateCon exists, then carry the same approved information through RateCon review, assignment, dispatch, delivery, invoice, payment, settlement, actual-profit review, and close without re-entry.

The authoritative sequence is:

`Offer → Profit check → Negotiate/Decline/Book → Await RateCon → RateCon review → Assignment → Dispatch approval → Driver acknowledgement → Pickup/In transit/Delivery → Documents → Invoice → Payment → Settlement → Actual profit → Closed`

## Non-negotiable rules

1. A RateCon is never required for the initial profitability decision.
2. Quote, booking, RateCon-confirmed, and actual financial stages are separate and immutable.
3. AI or document extraction may propose facts; deterministic code calculates money.
4. Material RateCon differences require human approval and never silently overwrite booking data.
5. Customer data is scoped to one organization at every query, URL, job, document, and audit event.
6. Financial input is strictly parsed; invalid text never silently becomes zero.
7. Historical results are never silently recalculated after a pay rule or formula changes.
8. Automated tests call no production provider.
9. Production schema changes require backup, dry run, compatibility review, rollback plan, and human approval.

## Release phases

### PR 1 — Architecture and Data Integrity

Deliver the audited baseline, Decimal strategy and parity fixtures, additive normalized schema, controlled load-state model, centralized role matrix, tenant/migration tests, rollback utility, public-copy corrections, and required design documents. Do not activate RateCon automation or deploy.

### PR 2 — RateCon to Dispatch

After PR 1 review: private document-provider boundaries, safe uploads, mock malware/OCR/extraction, evidence and confidence, candidate matching, difference approval, assignment ranking, recalculation, dispatch approval, and minimal driver acknowledgement.

### PR 3 — Delivery to Cash

Driver status/documents, detention/accessorial review, invoice packet and invoice-payment ledger, partial/final payment, versioned immutable settlements, quote/booked/actual comparisons, and profit-leak alerts.

### PR 4 — Production Beta Hardening

Managed PostgreSQL, SQLAlchemy/Alembic cutover, background jobs, complete roles/authentication, private object storage, observability, staging/production gates, CI/security expansion, backup restoration, accessibility/mobile evidence, and closed-beta readiness.

## PR 1 acceptance criteria

- Baseline tests and dependency audit are recorded.
- Routes, templates, tables, migrations, calculations, tests, raw SQL, float money, and public claims are inventoried reproducibly.
- All seven pay models have golden expected values.
- Decimal and legacy quote paths agree to the cent on every golden case.
- Money parser rejects invalid, Boolean, negative-disallowed, and non-finite values.
- Currency uses one documented half-up rounding policy.
- Normalized driver pay, power unit, trailer, assignment, stop, revenue, expense, status-history, and financial-snapshot tables exist additively.
- Legacy data, record counts, tenant IDs, and revenue cents validate after migration.
- Public UUIDs are backfilled for protected resources.
- Load transitions are controlled, audited, tenant-scoped, and retry-safe.
- Audit events and financial snapshots are append-only.
- Migration defaults to a verified backup dry run; apply/rollback require an explicit backup path.
- Public demo and SEO name only available capabilities.
- Full regression, migration, static syntax, and dependency checks pass.
- A draft PR is created but not merged or deployed.

## Explicitly deferred from PR 1

RateCon file storage/OCR/extraction, commercial routing, assignment ranking, driver portal, invoices/payments ledger, approved settlements, PostgreSQL, MFA/invitations, background jobs, production object storage, monitoring, expanded CI, and the 42-step end-to-end test. Foundation types or schema may anticipate those flows, but no public availability claim is permitted.

## Metrics for the eventual five-carrier beta

- 100% financial parity for approved historical fixtures.
- 0 cross-tenant access failures.
- 0 duplicate loads, documents, payments, or transitions under retry tests.
- At least 95% of booked fields reused without re-entry after booking.
- 100% material RateCon differences require explicit approval.
- 100% invoices reconcile to revenue items and payments.
- 100% approved settlements reconcile to stored line items.
- Successful backup restoration within the documented recovery objective.

## Go/no-go ownership

Financial changes, authentication, billing, migrations, tenant isolation, and production promotion require explicit human approval. No single automated agent may merge or deploy those changes independently.
