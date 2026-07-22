# Changelog

## 0.16.0a1 — Unreleased

- Added a strict Decimal/cents money policy with centralized half-up rounding and invalid-input rejection beside the protected legacy calculation path.
- Added frozen golden expected values and legacy-versus-Decimal parity tests for all seven supported pay models.
- Added additive schema-13 foundations for effective-dated driver pay rules, power units, trailers, equipment assignments, ordered load stops, load assignments, cents revenue/expense items, status history, and immutable financial snapshots.
- Added public UUID backfill, tenant-scoped migration validation, audit/snapshot immutability, and a controlled idempotent load-state transition service.
- Added a centralized least-privilege role-permission matrix; route enforcement remains a later reviewed change.
- Added backup-first dry-run/apply/rollback migration tooling and validation documentation. No production migration or deployment is included.
- Corrected public marketing, demo, and SEO copy to identify fictional estimates and the seven pay models the backend actually supports.
- Added the v0.16 current-state audit, requirements, architecture, migration, threat, rollback, test, parity, tenant, role, validation, and public-claims reports.
- Recorded the direct OTW workbook fixture refresh as blocked until the approved spreadsheet artifact runtime is available; the customer-facing financial engine remains unchanged.

## 0.15.0 — 2026-07-21

- Added privacy-first RateCon, business-bank-statement, and bill-statement audits with structured discrepancies and suggested review actions.
- Added explicit review boundaries: raw uploads are discarded, findings never silently change accounting/load values, and bank comparisons are not general-ledger reconciliation.
- Added a 14-step new-carrier startup checklist with official IRS, FMCSA, Clearinghouse, UCR, and IFTA resources.
- Added equipment purchase and finance scenario audits plus 90-day operating growth signals.
- Added the $10/month Carrier Startup plan with a zero-active-unit entitlement and fixed zero-unit limit enforcement.
- Added tenant-scoped document-audit history and startup progress to company exports.
- Upgraded database schema to version 12.

## 0.14.0 — 2026-07-21

- Added structured pickup and delivery addresses, appointment windows, contacts, and driver instructions.
- Added a verified RateCon-received checkpoint without storing RateCon PDFs.
- Added review-before-send SMS composition for iPhone and Android.
- Added Apple Maps and universal Google Maps navigation links for each stop in both the page and driver text.
- Added clear readiness blockers when the RateCon, driver phone, address, or appointment window is missing.
- Upgraded database schema to version 11.

## 0.13.0 — 2026-07-21

- Added the Phase 1 manual offer, profit check, negotiation, driver comparison, and quote-to-load workflow.
- Added immutable quote/booking snapshots and append-only negotiations.
- Added sourced driver locations with freshness warnings.
- Added exactly-once conversion to `Booked — Awaiting RateCon`.
- Added company-specific rate recommendation thresholds.
- Preserved workbook-parity math, seven pay models, and owner distribution.
- Updated public marketing and customer navigation.
- Upgraded database schema to version 10.

## 0.12.0 — 2026-07-21

- Added editable/cancelable loads and editable/voidable payments.
- Added Excel-style load filtering, sorting, reporting, and export.
- Corrected owner-pay and driver-balance workflows.
