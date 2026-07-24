# Changelog

## 0.16.0a12 - Google Analytics

- Installed the `G-RMCP51Y4Y7` Google Analytics 4 tag across the CarrierOS website and application.
- Configured analytics page locations without URL query parameters so reset tokens and other query values are not sent as page-location data.
- Expanded the Privacy Policy with a plain-language Google Analytics disclosure and opt-out information.

## 0.16.0a11 - Google Search Console verification

- Added the public Google Search Console verification tag for the canonical `https://otwcarrieros.com/` URL-prefix property.
- Preserved the verification tag across every public template so Google can continue validating ownership after deployment.

## 0.16.0a10 - CarrierOS search architecture

- Added a crawlable CarrierOS Solutions hub and nine people-first pages for small-fleet TMS, dispatch, RateCon review, document management, receivables, compliance, owner-operators, box-truck fleets, and hotshot carriers.
- Expanded the four existing search landing pages with practical operating detail, product boundaries, FAQs, and contextual internal links.
- Corrected the server-level `noindex` conflict on the public Help Center and its 20 product guides.
- Added breadcrumb, website, organization, founder, software, FAQ, and help-article structured data with unique canonical titles and descriptions.
- Expanded homepage, demo, checkout, help, footer, robots, and sitemap connections so crawlers and people can reach the full public content architecture.

## 0.16.0a9 - CarrierOS help center

- Added a public, searchable help center with step-by-step operating guides for every workspace tab.
- Added a guided offer-to-cash workflow, related-guide navigation, product boundaries, operating tips, and responsive mobile layouts.
- Linked the help center from the customer workspace, mobile menu, marketing resources, public footer, and XML sitemap.
- Added route, content, canonical-link, navigation, and sitemap coverage for the complete guide library.

## 0.16.0a8 - Driver referral program draft

- Added OTW-administered private driver invitations, secure activation and earnings portals, versioned referral terms acceptance, and unique public referral links.
- Added first-touch signup attribution and a recurring 50% commission ledger for successful CarrierOS subscription invoices, with a 30-day confirmation hold and idempotent Stripe processing.
- Added refund, void, and dispute adjustments; private driver earnings portals; and an administrator-controlled manual payout ledger.
- Added self-referral blocking, required promotional-disclosure copy, noindex controls, token-path log redaction, and referral privacy and operations documentation.

## 0.16.0a4 - Phase 4 draft

- Added a non-mutating production release-readiness gate for live billing, secure document storage, managed malware scanning, database integrity, schema version, and verified backup evidence.
- Added JSON/console operator output and focused tests; Phase 4 remains a draft and is not deployed.
- Added a hard-launch checklist that separates automated evidence from required Render, Stripe, email, legal, security, and human-approval actions.

## 0.16.0a3 — Draft

- Added the first Phase 3 delivery-to-cash slice: controlled pickup, transit, delivery, and documents-pending status updates from the signed driver dispatch link.
- Added retry-safe, tenant-scoped delivery transitions with append-only history and audit events; driver links cannot skip states or advance invoice/payment states.
- Added private BOL, POD, receipt, and detention-evidence uploads with signature/size/page validation, malware screening, organization/load-prefixed storage, and office-review records.
- Added office delivery execution history and private delivery-document review/download surfaces to load details.
- Added Phase 3 migration version 15, integration coverage, and explicit documentation of deferred invoice, payment, settlement, and variance work.

## 0.16.0a2 — 2026-07-21

- Added the Phase 2 RateCon inbox with PDF/JPEG/PNG signature validation, size/page limits, organization-prefixed private object keys, duplicate checks, retention metadata, and audited signed download links.
- Added storage, malware scan, OCR, and extraction provider boundaries with deterministic mocks and a manual production fallback; uploads remain disabled when encrypted storage is not configured, and dispatch remains blocked until malware screening passes.
- Added immutable extraction runs and evidence-bearing fields with confidence, page, provider/version, human review, and tenant-scoped candidate matching.
- Added booking-versus-RateCon comparison with explicit financial and operational difference classifications and human approval for material changes.
- Added ranked driver, power-unit, and trailer assignment using saved locations, schedule conflicts, compliance expirations, equipment compatibility, equipment-specific profitability, and a mandatory HOS disclaimer.
- Added final dispatch approval and a short-lived, single-load driver acknowledgment link with stops, facility time zones, contacts, instructions, and Apple/Google navigation without fleet financial access.
- Added normalized dual writes for newly created power units, trailers, drivers, quote-booked loads, manual loads, stops, assignments, revenue items, status history, and immutable booking/RateCon snapshots.
- Added additive schema version 14 and Phase 2 rollback support, tenant/provider/workflow tests, updated privacy disclosures, and Phase 2 operating documentation.

## 0.16.0a1 — 2026-07-21

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
