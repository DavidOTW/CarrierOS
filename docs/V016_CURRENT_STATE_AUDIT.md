# CarrierOS v0.16 Current-State Audit

Status: PR 1 review baseline

Branch: `agent/v016-architecture-data-integrity`

Baseline commit: `7d1e6f6` (`origin/main`)

Audit date: 2026-07-21

## Executive finding

CarrierOS v0.15 is a functioning multi-tenant FastAPI/Jinja application with a broad carrier-operations surface, but it is not yet the complete v0.16 workflow and must not be represented as generally production-ready. The largest architecture risks are binary floating-point financial calculations, an embedded SQLite/raw-SQL persistence layer, combined driver/equipment records, free-text legacy load statuses, incomplete role enforcement, and feature claims that previously exceeded the implemented driver-pay and settlement workflows.

PR 1 creates additive, reviewable foundations without changing the customer-facing calculation engine or deploying a production schema. RateCon automation, driver dispatch, invoicing, versioned settlements, PostgreSQL cutover, and production beta hardening remain later phases.

## Exact baseline

- Existing automated suite before PR 1: **56 passed**.
- Existing dependency scan: `pip-audit` completed successfully with **0 known vulnerabilities reported**.
- Baseline warnings: Starlette's legacy `TestClient`/`httpx` deprecation and a local pytest-cache permission warning. Neither changed test results.
- Framework: FastAPI, Jinja, Python standard-library `sqlite3`.
- Runtime data store: one SQLite database and one application replica on Render.
- Billing system of record: Stripe Billing through server-created Checkout and verified webhooks.

## Repository inventory

At PR 1 review time the reproducible inventory reports:

- 97 FastAPI route decorators in `app/main.py`.
- 41 Jinja templates.
- 35 declared SQLite tables: 24 legacy tables plus 11 additive v0.16 foundation tables.
- 1 versioned v0.16 migration specification.
- 62 Python test definitions; parametrization creates 80 collected tests.
- 252 raw-SQL helper/connection calls across application Python after the additive foundation: `app/db.py` 42, `app/main.py` 150, `app/services.py` 8, `app/load_states.py` 6, and `app/v016_migration.py` 46.
- Float/SQLite `REAL` money-risk markers remain concentrated in `app/db.py`, `app/calculations.py`, `app/main.py`, `app/opportunities.py`, `app/audits.py`, `app/services.py`, `app/growth.py`, and `app/routing.py`.

Run `python scripts/v016_inventory.py` for every file, line number, call site, and public-claim candidate. This inventory is deliberately executable so later PRs cannot rely on a stale hand-maintained list.

## Current capability versus v0.16 target

| Area | Current capability | Material gap |
|---|---|---|
| Offer decision | Manual offer, deterministic quote, driver comparison, negotiation, exactly-once booking | No RateCon automation should be inserted before this decision |
| Financial math | Protected v0.15 float formulas with regression tests | Customer path still uses float; strict Decimal path is side-by-side only |
| Driver pay | Seven implemented models and cumulative payment tracking | Effective-dated, approved rules and immutable settlements are not active |
| Driver/equipment | Combined legacy driver, vehicle, and cost fields | Normalized tables are migrated but not yet the route source of truth |
| Load operations | Loads, two stop fields, edits/cancellation, filters, payment correction | Normalized stops/assignments/state machine are staged but not wired to routes |
| RateCon | Limited, text-based audit and manually verified dispatch details | No private retained object, OCR, evidence-level extraction, or material-difference approval |
| Receivables | Invoice/detention records and payment dates | No invoice-payment ledger, packet workflow, partial/short-payment lifecycle |
| Settlement | Driver balance/pay records | No versioned approved immutable settlement record |
| Tenancy | `organization_id` filters are broadly present | Raw SQL remains easy to misuse; comprehensive IDOR matrix is not complete |
| Roles | Legacy account behavior | Central matrix exists in PR 1 but is not enforced on routes yet |
| Database | SQLite schema version 12 baseline | Managed PostgreSQL/SQLAlchemy/Alembic migration is not implemented |
| Public claims | Strong SEO/marketing site | Unsupported hourly/salary and approved/live-settlement language required correction |

## Financial-risk inventory

The protected calculation engine intentionally remains untouched in PR 1. Its permissive `_num` helper can convert invalid text to defaults, and currency flows through Python floats and SQLite `REAL`. Changing those in place would risk silently changing historical results.

PR 1 therefore adds:

- strict `Decimal` parsing and centralized `ROUND_HALF_UP` rules;
- integer-cent, basis-point, and rate-micro storage converters;
- a parallel Decimal quote implementation;
- golden expected values for all seven pay models;
- cent-level comparison tests between legacy, Decimal, and fixture results;
- additive integer-cent tables for new revenue, expense, and financial snapshots.

The customer-facing engine does **not** switch in this PR. That switch requires reviewed workbook fixtures, dual-run telemetry, explicit approval of every difference, and immutable historical snapshots.

## OTW workbook evidence gap

The current OTW workbook was located at the user-provided desktop path and was not modified. The required artifact runtime for safe workbook inspection was unavailable in this execution environment, so new fixtures could not be extracted directly from that file without violating the spreadsheet handling rules. PR 1 uses the protected v0.15 outputs for all seven models. Refreshing the fixtures from the actual workbook remains a human-review gate before the Decimal path can become authoritative.

## Public-claims audit

Corrected in PR 1:

- “Turn a rate confirmation into a decision” now says “Turn a broker offer into a profit decision.”
- The public demo now lists the seven pay models actually supported by the backend.
- Hourly and salary pay claims were removed.
- “Real-time” fictional dashboard language was replaced with “Fictional sample.”
- Approved settlement language was changed to estimated driver pay/payment tracking.
- SEO text now distinguishes estimates from accounting, payroll, and settlement approval.

Automated public-copy tests guard these specific regressions. The route slug `/driver-settlement-software` is retained for link continuity, but the page title and visible copy accurately describe driver-pay tracking.

## Raw SQL and database assessment

Raw SQL is pervasive rather than isolated behind repositories. Parameter binding is common, but tenant scoping depends on every call site remembering `organization_id`. PR 1 does not attempt a high-risk full rewrite. The approved target is:

1. add normalized, tenant-keyed tables and public UUIDs;
2. validate legacy-to-normalized migration with record and money totals;
3. introduce repositories/transactions around the normalized model;
4. dual-read/dual-write under flags;
5. migrate production to managed PostgreSQL with SQLAlchemy 2.x and Alembic;
6. enable PostgreSQL constraints/locking and row-level security where practical;
7. retire legacy fields only after parity, rollback, and human approval.

## Immediate risks and controls

| Risk | Current control | Remaining action |
|---|---|---|
| Financial drift | Legacy engine preserved; golden comparisons | Approve workbook-derived fixtures and switch plan |
| Cross-tenant access | Existing filters; new tenant-isolation tests | Repository layer, route permission enforcement, broader IDOR suite |
| Migration loss | Additive schema; backup-first dry run; validation and rollback | Test on a current production backup; human approval |
| Historical recalculation | Existing data retained; immutable new snapshots | All later stages must reference snapshot IDs |
| Overstated product claims | Corrected copy plus tests | Repeat claims audit in every release |
| Role escalation | Central least-privilege matrix | Wire it to every route in a separate reviewed change |
| SQLite concurrency | One-replica deployment | Managed PostgreSQL before beta production |

## Review gate

Do not begin PR 2 RateCon automation until reviewers approve the normalized model, money policy, migration/rollback design, tenant boundary, and known workbook-fixture gap.
