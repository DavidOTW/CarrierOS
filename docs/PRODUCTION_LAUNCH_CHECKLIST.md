# CarrierOS production launch checklist

This checklist separates what the code can verify from the operator actions
that require Render, Stripe, an email provider, and qualified professional
review. A hard launch should not be announced until every **Blocker** is
closed and recorded by a human owner.

## Code and deployment gates

- [x] GitHub Actions test, lint, compile, and dependency-audit checks pass.
- [x] Public pages, signup, demo, assets, sitemap, and security headers pass
      smoke checks.
- [x] Private routes redirect unauthenticated visitors to `/login`.
- [ ] Merge and deploy the current Phase 4 PR.
- [ ] Confirm `/health/ready` returns `200` in the production environment.
- [ ] Confirm the production version is the reviewed commit, not an older
      Phase 3 deployment.

## **Blocker — data and document safety**

- [ ] Set `CARRIEROS_STORAGE_ENCRYPTED_AT_REST=true` only after verifying the
      persistent storage provider's encryption-at-rest controls.
- [ ] Configure a real malware scanner adapter. `manual` and `mock-clean` are
      not production release gates.
- [ ] Keep RateCon and delivery-document workflows disabled until both checks
      are green; do not market them as automated production features before
      then.
- [ ] Move customer data to managed PostgreSQL before heavy traffic or a
      multi-instance deployment.
- [ ] Copy logical backups off-host and complete a documented restore rehearsal.

## **Blocker — billing and customer operations**

- [ ] Verify all five live Stripe Prices match CarrierOS amounts, monthly
      recurrence, USD currency, and licensed usage.
- [ ] Complete one live-mode Checkout trial with a controlled customer account.
- [ ] Verify signed webhook handling for checkout, subscription changes,
      cancellation, trial ending, paid invoice, and failed invoice.
- [ ] Verify Customer Portal plan changes, payment-method updates, and
      cancellation behavior.
- [ ] Configure a verified SMTP sender and test password recovery.
- [ ] Publish a monitored support mailbox and response procedure.

## Legal, security, and marketing gates

- [ ] Have counsel review the Terms, Privacy Policy, subscription language,
      trial/cancellation language, and document-data disclosures.
- [ ] Complete an independent security review before accepting sensitive
      financial or identity documents.
- [ ] Add uptime, error-rate, backup, billing-webhook, and storage-failure
      alerts.
- [ ] Make the marketing site state clearly that estimates are informational,
      RateCon automation is gated, and CarrierOS is not payroll, accounting,
      legal, tax, insurance, or regulatory advice.
- [ ] Start with a closed beta and support capacity before buying heavy traffic.

## Final approval record

Record the reviewed commit, production environment audit, Stripe test evidence,
backup path/checksum, restore result, reviewer, rollback owner, and approval
date. The readiness script and `/health/ready` endpoint provide evidence; they
do not replace this human approval.
