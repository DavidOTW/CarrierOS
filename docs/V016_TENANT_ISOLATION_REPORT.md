# CarrierOS v0.16 Tenant-Isolation Report

Status: PR 1 foundation; not a closed-beta certification.

## Boundary

Tenant identity must originate from the authenticated session. Internal numeric IDs or public UUIDs are record locators, never authorization. Every read, insert, update, delete, transition, job, export, audit record, and future object key must also be constrained by `organization_id`.

## PR 1 evidence

- Every additive normalized business table stores `organization_id`.
- Migration validation rejects a load assignment whose driver or power unit belongs to another organization.
- State transitions select and update by both load ID and organization ID.
- State-history idempotency keys are unique within an organization.
- Cross-tenant transition attempts return not found and do not create history.
- Public UUIDs are backfilled for drivers, vehicles, loads, and opportunities to reduce sequential-ID exposure.
- The centralized Driver role contains only assigned-load, status, document-upload, and own-settlement permissions.

## Residual gaps

- Existing application routes still contain pervasive raw SQL and must be reviewed/wrapped in tenant-required repositories.
- The centralized permission matrix is not yet enforced on every route.
- Full cross-tenant URL/API/update/delete/export/document/job tests are not complete.
- PostgreSQL row-level security is not available while production remains SQLite.
- Future object storage, background jobs, and signed URLs do not yet exist and therefore cannot be certified.

## Beta gate

Before closed beta, a two-organization automated matrix must prove denial across every record type and operation, including guessed internal IDs/public UUIDs, driver views, documents and signed URLs, exports, jobs, invoices/payments, settlements, audit logs, and Stripe references. PostgreSQL must retain application checks and add selected RLS policies. Independent security review remains required.

## Result

**Pass for PR 1 state-transition and migration foundation; no-go for production tenant-isolation certification.**
