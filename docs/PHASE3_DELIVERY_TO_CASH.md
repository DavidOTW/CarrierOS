# CarrierOS v0.16 PR 3 — Delivery to Cash (first slice)

## Scope in this draft

This draft extends the approved RateCon-to-dispatch workflow with the first controlled
delivery-execution boundary:

- Driver dispatch links can advance a load through `AT_PICKUP`, `IN_TRANSIT`,
  `AT_DELIVERY`, and `DELIVERED_DOCUMENTS_PENDING`.
- Every transition is tenant-scoped, append-only, audited, and retry-safe through an
  idempotency key. Drivers cannot skip a state or advance a load through invoice/payment
  states.
- An assigned driver can upload a BOL, POD, receipt, or detention-evidence file from the
  signed dispatch link. The file is signature-checked, size/page limited, malware-screened,
  stored under an organization/load-prefixed private key, and held in `PENDING` office
  review.
- Office users can update a controlled delivery status from the load detail page and can
  review/download the private delivery documents through the existing permissioned
  operational-document boundary.

The driver link remains single-load, signed, and time-limited. It exposes no company-wide
financial information and includes a parked/safety warning.

## Explicitly deferred

Invoice packets, detention/accessorial approval, invoice and payment ledgers, partial/final
payment reconciliation, immutable settlement revisions, booked-versus-actual variance
alerts, background processing, production object storage, and managed PostgreSQL remain
subsequent PR 3/PR 4 work. No public claim should describe those capabilities as live.

## Verification

The draft includes a tenant-scoped integration test covering a driver status transition,
same-key retry behavior, out-of-order rejection, private storage, malware-clean document
upload, and the delivery-document link. The full regression suite and Ruff checks must pass
before this draft is considered for review or production promotion.
