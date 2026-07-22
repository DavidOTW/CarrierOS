# CarrierOS v0.16 PR 2 — RateCon to Dispatch

## Workflow delivered for review

`Booked — Awaiting RateCon → RateCon Review → Needs Assignment → Dispatch Awaiting Approval → Dispatched — Awaiting Driver Acknowledgment → Dispatch Acknowledged`

The broker offer and booking snapshot remain the source of the agreed terms. A RateCon is
uploaded only after booking. Extracted values are proposals with provider, version,
confidence, page, and evidence; deterministic application code compares them with the
booking. Material financial or operational differences require explicit human approval.

## Document boundary

- PDF, JPEG, and PNG are accepted only after signature validation; PDFs are parsed for a
  maximum of 25 pages and every file is capped at 12 MB.
- Object keys are organization-prefixed and never served from a public static directory.
- Authenticated users request a five-minute signed application download token; issuance and
  download are audit events.
- Duplicate checksum/type/load combinations are rejected.
- Production upload is disabled unless the configured storage is asserted encrypted at
  rest. Dispatch is blocked unless malware status is `CLEAN`.
- Digital-PDF label extraction is conservative. Scanned documents use an OCR provider port;
  the default production fallback is human entry, not invented OCR or credentials.
- Raw document text is never written to ordinary application logs.

The current local-volume adapter is suitable only on an encrypted managed persistent volume.
An S3-compatible production adapter and managed asynchronous scanning/extraction are still a
PR 4 gate. No public availability claim is made by this pull request.

## Matching and comparison

Candidate scores use load number, broker/customer, pickup date, delivery date, and rate.
CarrierOS displays candidates and never attaches an uncertain upload automatically. The
comparison preserves booked and RateCon values and classifies `MATCH`, `MINOR DIFFERENCE`,
`FINANCIAL DIFFERENCE`, `OPERATIONAL CONFLICT`, or `REVIEW REQUIRED`. Rate decreases,
appointment changes, added stops, tracking penalties, driver assist, and factoring
restrictions are material.

## Assignment and dispatch

Ranking evaluates saved driver location/freshness, active power unit, trailer compatibility,
scheduled-load conflicts, saved compliance expirations, deadhead source, driver pay,
company profit, margin, and profit per day. The selected assignment remains a human action.
CarrierOS always displays: “Schedule estimate only — driver HOS must be independently
verified.” No HOS, GPS, or ELD availability claim is made.

Assignment approval stores a separate RateCon-confirmed calculation snapshot and advances
the controlled state machine. Final dispatch approval is a separate permission. The driver
receives a signed 48-hour, single-load page with stops, facility time zones, contacts,
instructions, and navigation links; it exposes no company-wide financial information and
records an idempotent acknowledgment.

## Deferred

- Production S3-compatible storage adapter and managed malware/OCR/extraction services.
- Background queues, retries, and extraction progress UI.
- Driver authentication/MFA/session administration.
- Pickup/transit/delivery statuses and BOL/POD/receipt uploads (PR 3).
- Commercial routing, PostgreSQL, RLS, and production observability (PR 4).
