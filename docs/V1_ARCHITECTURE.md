# CarrierOS V1 Architecture

## Current system

CarrierOS is a server-rendered FastAPI application deployed as one Docker service. Jinja templates and a small progressive-web-app shell provide the browser UI. SQLite is the transactional store on a persistent Render disk. Stripe Billing is the subscription system of record.

```text
Browser
  -> HTTPS / signed session / CSRF
FastAPI routes and server-rendered views
  -> opportunity engine
  -> established load calculation engine
  -> organization-scoped services
  -> Stripe and SMTP adapters
SQLite + daily logical backups
```

## Phase 1 boundaries

- `app/calculations.py`: established deterministic load and quote math. Kept intact for workbook parity.
- `app/opportunities.py`: offer-specific aggregation, threshold checks, rate recommendations, snapshots, and driver comparisons.
- `app/routing.py`: provider boundary. Manual production default, estimated development adapter, deterministic test adapter.
- `app/db.py`: schema, idempotent migrations, transactions, tenant export, immutable triggers.
- `app/main.py`: authentication, authorization, validation, HTML routes, booking transaction, and audit events.

The opportunity engine calls the established quote calculation instead of reimplementing pay rules. Revenue-dependent factoring and quick-pay fees are added as direct costs before evaluating thresholds.

## Data model

### `load_opportunities`

Mutable working record for an offer. It preserves the original offer, current counteroffer, final agreement, lane/service details, selected driver/unit, miles, expenses, status, and the one allowed `booked_load_id`.

### `opportunity_snapshots`

Immutable JSON input/result envelope. `stage` is `evaluation` or `booking`; `revision` is monotonically increasing within the stage. Database triggers reject updates and deletes. The input records the company thresholds and complete selected driver pay profile used at that time.

### `opportunity_negotiations`

Append-only offer, counteroffer, decline, and booking history. Database triggers reject updates and deletes.

### `driver_locations`

Append-only sourced location history with observed time, source, confidence, optional coordinates, and override reason.

### `loads`

Phase 1 adds `opportunity_id`, original/final rates, snapshot references, and RateCon due time. A partial unique index on `opportunity_id` prevents duplicate conversion.

## Booking transaction

One SQLite transaction:

1. Re-read the tenant-scoped opportunity.
2. Reject an already-booked record.
3. Locate the latest evaluation snapshot.
4. Insert the immutable final booking snapshot.
5. Insert the operational load.
6. Update the opportunity with the load reference and final rate.
7. Append the booking event.

Any failure rolls back all seven operations. The database unique index remains a second line of defense against races.

## Recommendation model

The engine evaluates:

- company margin target;
- minimum total company profit;
- minimum company profit per total mile;
- minimum company profit per trip day;
- minimum revenue per total mile;
- maximum deadhead percentage.

`BOOK` means all configured thresholds passed. `NEGOTIATE` means a higher rate can meet them. `DECLINE` means the offer loses money or a feasible target cannot be found. `REVIEW REQUIRED` means critical input or operational confidence is incomplete. These are deterministic decision aids, not promises.

## Security and tenancy

- Signed, secure production cookies and production CSRF verification.
- PBKDF2-SHA256 password hashes at 600,000 iterations.
- Subscription entitlement checked before workspace access.
- Every opportunity/location/snapshot/history query includes the authenticated organization.
- Foreign keys and organization IDs are retained on all new tables.
- Sensitive integrations use environment variables only.
- Audits store identifiers and event metadata, not full customer records or credentials.

## Scaling path

SQLite requires a single application replica. Before horizontal scaling, migrate the same normalized schema to PostgreSQL, add transaction-level row locking for booking, and use a managed job queue for reminders and document processing. Private document storage and signed URLs are Phase 2 prerequisites.

