# CarrierOS v0.16 Threat Model

## Scope and trust boundaries

This model covers browser/mobile sessions, FastAPI routes, application services, database access, Stripe webhooks, future background jobs, and future private document providers. PR 1 implements only the data-integrity foundation; later controls remain release gates.

## Assets

- Organization-scoped operational and financial records.
- Driver identity/contact and future private documents.
- Calculation inputs, versions, line items, and snapshots.
- Session, reset, invitation, webhook, and idempotency tokens.
- Stripe customer/subscription references and webhook evidence.
- Audit history, backups, and migration reports.
- Provider credentials and private object keys.

CarrierOS must not collect Social Security numbers, banking credentials, full account numbers, tax IDs, identity-document images, or other data outside the documented need.

## Actors

- Legitimate Owner, Administrator, Dispatcher, Accounting, Compliance, Read-only, and Driver users.
- Compromised or malicious tenant user.
- Unauthenticated internet attacker.
- Malicious upload/document.
- Spoofed external provider or webhook sender.
- Operational insider with database or hosting access.
- Automated retry causing duplicate state or money effects.

## Threats and controls

| Threat | Impact | PR 1 control | Required before beta |
|---|---|---|---|
| Cross-tenant IDOR | Disclosure or mutation of another carrier's data | Tenant-keyed normalized tables, tenant-scoped transition tests, public UUIDs | Repository enforcement and exhaustive URL/API/document/job tests; selected PostgreSQL RLS |
| Role escalation | Unauthorized money, dispatch, compliance, or admin action | Central least-privilege matrix and tests | Enforce permissions server-side on every route; invitation/MFA/session tests |
| Financial tampering/drift | Incorrect quote, pay, profit, or settlement | Strict Decimal primitives, golden parity tests, cents line items, immutable snapshots | Workbook approval, approved-settlement ledger, reconciliation and revision workflow |
| Invalid numeric coercion | Malformed text becomes zero | Strict parser rejects invalid/non-finite/Boolean input | Wire parser to every financial form/API/import and display field errors |
| Audit destruction | Conceals changes | Append-only SQLite audit and snapshot triggers | Restricted PostgreSQL role, append-only API, off-host audit/backup retention |
| Duplicate retry | Duplicate load/payment/status/document | Tenant-unique transition idempotency; existing booking/webhook defenses | Unique keys on all write workflows and background jobs |
| SQL injection | Data compromise | Parameter binding is common | Repository/query review, static scanning, no dynamic user-controlled identifiers |
| Session/CSRF attack | Unauthorized browser action | Existing sessions and CSRF checks | Full route coverage, fixation/revocation tests, recent-login reauthentication |
| Token theft/replay | Account takeover | Existing reset token behavior; hashed onboarding compatibility | Hashed invitation tokens, one-use enforcement, expiry, MFA for privileged users |
| Webhook spoof/replay | False entitlement/payment state | Signature verification and idempotent event store | Complete lifecycle integration tests and alerting |
| Malicious upload | Malware, parser exploit, data leak | Raw limited audit uploads discarded today | Signature/size/page checks, private object storage, malware scan, sandboxed async extraction |
| Public object access | Document disclosure | No full retained object workflow in PR 1 | Tenant prefix, encryption, signed short URLs, access log, retention/deletion |
| Sensitive logs | PII or secret disclosure | Existing bearer-token redaction | Structured safe context, document/phone/license/token redaction tests |
| Provider outage/manipulation | Bad route/extraction or blocked operation | Manual routing boundary | Feature flags, provenance, timeout/retry, mocks, manual fallback, contract tests |
| Migration failure | Loss or financial mismatch | Backup-first additive migration, savepoint, count/money validation, rollback | Production-copy rehearsal and human approval |
| Backup failure | Irrecoverable records | Existing local backup mechanism | Off-host encrypted backups, restore drill, health alert |

## Abuse cases

1. A Driver changes a UUID to access another driver's load: server must bind the user to the assigned driver and organization, returning indistinguishable not-found behavior.
2. A Dispatcher submits an Accounting endpoint: server permission middleware/dependency must reject it even if the UI hides the button.
3. A tenant retries a state transition: the same idempotency key returns the original history row; reuse for another load fails.
4. An attacker uploads a renamed executable: signature validation rejects it before storage/extraction.
5. A forged Stripe event or repeated valid event arrives: invalid signatures fail and valid event IDs apply once.
6. A user changes a pay rule after settlement approval: the old snapshot remains unchanged; correction requires a superseding/reversal record.
7. An operator runs a migration against production without a backup path: the utility refuses; the release process still requires human approval.

## Residual risk accepted for PR 1 review only

- Customer-facing calculations still use legacy floats.
- Central permissions are not yet route-enforced.
- Raw SQL and SQLite remain the live persistence model.
- Normalized tables are not yet dual-written by current routes.
- There is no secure retained RateCon object/OCR workflow.
- Independent security testing has not occurred.

These are blockers for closed-beta production, not reasons to hide PR 1 behind public availability claims.
