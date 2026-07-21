# CarrierOS V1 Implementation Plan

## Phase 0 — Audit and safety baseline (complete)

- Inventoried Python modules, templates, static assets, tests, deployment files, and existing documentation.
- Ran the pre-change suite: 44 tests passed.
- Confirmed the calculation engine, tenant isolation pattern, Stripe entitlement flow, blank-customer signup, backups, and workbook-parity coverage.
- Identified the primary gaps: no persisted opportunity, no negotiation history, no immutable quote snapshot, no driver location provenance, and RateCon incorrectly implied as the beginning of the workflow.

## Phase 1 — Offer to booked load (complete in v0.13.0)

- Rate Quote list, quick entry, advanced entry, edit/version, and detail views.
- Profit Check with company thresholds and `BOOK / NEGOTIATE / DECLINE / REVIEW REQUIRED` recommendation.
- Driver comparison with sourced/stale locations, deadhead-provider boundary, schedule conflicts, compliance warnings, and unit checks.
- Negotiation history and copyable counteroffer message.
- Single-transaction quote-to-load conversion.
- `Booked — Awaiting RateCon` status and due time.
- Immutable evaluation and booking snapshots.
- Tenant export and migration coverage.
- Public copy updated to say profit checking starts with the broker offer.
- Full suite after implementation: 48 tests passed.

## Phase 2 — RateCon and execution (planned, not implemented)

- Private object storage with malware scanning and signed downloads.
- RateCon upload after booking, extraction confidence, human review, and booked-vs-document discrepancy workflow.
- Dispatch tendering, driver acknowledgement, load check calls, exception management, appointment and stop details.
- BOL/POD workflow, delivery confirmation, and operational document retention.
- Background job runner for RateCon reminders and execution alerts.

Exit criteria: no public automation claim until extraction/reconciliation tests, storage security review, and failure recovery pass.

## Phase 3 — Settlement, billing, and collections (planned, not implemented)

- Settlement approval and statement generation from immutable pay-rule snapshots.
- Invoice creation, document packet assembly, payment terms, aging, collections activity, and accounting export/sync.
- User roles and permissions for owner, dispatcher, office, and driver experiences.
- PostgreSQL migration and horizontally safe background processing.

Exit criteria: financial reconciliation suite, authorization matrix tests, restore drill, and independent security review.

## Release process

1. Run syntax compilation and all automated tests.
2. Review migration on a copy of production data and create an off-host backup.
3. Merge through a reviewed pull request.
4. Allow Render to deploy `main` to one instance.
5. Verify `/health`, login, empty-customer isolation, quote creation, booking, and duplicate prevention.
6. Monitor application logs and database disk metrics.
7. Roll back application image only with database compatibility confirmed; never discard the production disk.

