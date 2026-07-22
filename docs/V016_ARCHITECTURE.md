# CarrierOS v0.16 Architecture

## Decision summary

PR 1 uses an additive strangler migration: the v0.15 SQLite/raw-SQL application remains operational while normalized v0.16 tables, strict money primitives, controlled state transitions, public UUIDs, append-only snapshots, and centralized permissions are introduced beside it. The legacy calculation path remains customer-facing until reviewed parity evidence authorizes a switch.

This is intentionally not the final production architecture. The beta target is FastAPI plus SQLAlchemy 2.x/Alembic on managed PostgreSQL, private S3-compatible storage, and managed background jobs. That cutover belongs to PR 4 after workflow and parity review.

## Boundaries

```text
Browser / mobile
      |
FastAPI routes + CSRF/session boundary
      |
Application services + centralized permissions
      |
Normalized repositories / transactions
      |
SQLAlchemy models + Alembic migrations
      |
Managed PostgreSQL (+ application tenant checks and selected RLS)

External providers are ports, never core dependencies:
storage | malware scan | OCR/extraction | route | geocode | time zone |
fuel price | email | SMS | Stripe
```

The current raw-SQL path remains beneath the route layer during PR 1. Later PRs introduce repository interfaces and feature-gated dual writes before any source-of-truth switch.

## Money architecture

- Application currency: Python `Decimal`, quantum `0.01`, `ROUND_HALF_UP`.
- New database currency: signed integer cents in SQLite foundation; PostgreSQL target may use `BIGINT` cents or `NUMERIC`, but one representation must be selected before cutover.
- Percentages: four decimal places in application logic and basis points for new normalized persistence where applicable.
- Per-mile/rate values: six decimal places and integer micros in normalized persistence.
- Parsing: empty values require an explicit default; invalid text, Booleans, infinities, and NaN are errors.
- Rounding: compute with controlled Decimal precision and round at stored line-item or published result boundaries, never through binary float.
- Historical loads: quote, booking, RateCon-confirmed, and actual stages store immutable input/output snapshots with calculation version and rounding policy.

PR 1's `calculate_quote_decimal` is a side-by-side comparator. Existing routes still call the protected legacy formulas. No production record is silently recalculated.

## Normalized domain model

Every tenant-owned table carries `organization_id`, and protected public resources receive UUIDs separate from sequential internal primary keys.

### People and pay

- `drivers`: legacy identity/contact record remains during migration.
- `driver_pay_rules`: effective dates, version, pay model, controlled rate/percentage storage, revenue/expense inclusion configuration, extra pay/deductions, approval metadata.
- `users.role`: normalized role value for the centralized permission matrix.

### Equipment

- `power_units`: unit identity and equipment-specific operating costs.
- `trailers`: trailer identity, dimensions/weight, and operating costs.
- `equipment_assignments`: driver/power-unit/trailer time range, provenance, approval, and uniqueness boundaries.

Legacy vehicle and driver equipment fields remain until dual reads/writes, calculation parity, and rollback validation are approved.

### Load operations

- `loads`: receives public UUID, controlled `status_code`, and update timestamp while preserving legacy columns.
- `load_stops`: ordered stop type, address, time zone, local/UTC windows, contact/instructions, arrival/departure, detention eligibility.
- `load_assignments`: driver/power unit/trailer, stage, provisional/approved state, deadhead and routing provenance.
- `load_revenue_items`: categorized immutable-friendly cents line items.
- `load_expense_items`: categorized cents line items.
- `load_status_history`: prior/new state, actor, timestamp, reason, and tenant-unique idempotency key.
- `load_financial_snapshots`: stage, version, immutable JSON inputs/outputs, cents totals, rounding policy, and creator.

## State machine

The canonical path begins at `BOOKED_AWAITING_RATECON` and proceeds through review, assignment, dispatch approval/acknowledgement, pickup/transit/delivery, documents, invoice, payment, settlement, and close. Cancellation is available only from safe pre-delivery states. Every transition:

- loads the record with both internal ID and organization ID;
- validates the target against the current state;
- requires an idempotency key;
- inserts an append-only history record;
- records actor, time, prior state, target state, and optional reason;
- updates the current status in the same transaction;
- returns the prior history record for an identical retry.

Arbitrary text is mapped only during legacy migration; new writes must use the enum.

## Authorization

The centralized roles are Owner, Administrator, Dispatcher, Accounting, Compliance, Read-only, and Driver. Permissions express actions (`loads.manage`, `money.manage`, `driver.loads.view_assigned`) rather than role-name checks. Driver grants are limited to assigned loads, operational status/documents, and the driver's own settlement. PR 1 defines and tests the matrix but does not claim route enforcement; wiring and IDOR verification are required before beta.

## Tenant isolation

Defense in depth target:

1. organization ID comes from the authenticated session, never a submitted hidden field;
2. every repository method requires an organization ID;
3. compound uniqueness and indexes include organization ID;
4. protected URLs expose public UUIDs rather than sequential IDs;
5. transactions re-check ownership on update/delete;
6. jobs and object keys carry immutable tenant context;
7. PostgreSQL uses selected row-level-security policies in addition to application checks;
8. cross-tenant tests cover read, update, delete, document, job, and API paths.

## Immutability and audit

SQLite triggers prevent update/delete of `audit_events` and `load_financial_snapshots`. PostgreSQL will replace these with database permissions/triggers and append-only repository methods. Corrections create superseding/reversal records rather than rewriting approved history.

## Provider architecture for later phases

Each integration provides a typed port, deterministic mock, manual fallback, feature flag, tenant-safe configuration, encrypted credentials, timeout/retry status, last success/error, disconnect path, and contract test. Missing production credentials must leave a visible manual workflow; no credentials are invented.

## Transaction and concurrency rules

- Booking conversion, state transitions, invoice payment application, settlement approval, and webhook processing require one transaction and a unique idempotency key.
- PostgreSQL uses row locks for mutable aggregate transitions.
- Financial snapshots and approved settlements are append-only.
- External calls are outside database locks and complete through retry-safe jobs.

## Adoption gates

The normalized path cannot become authoritative until migration validation, seven-model workbook parity, tenant isolation, route permissions, rollback rehearsal, backup restoration, and explicit review pass. PostgreSQL cannot receive production data until a production backup copy passes count and financial-total reconciliation.
