# CarrierOS operations handoff

This document records the steps that require the product owner to create an
account, approve a recurring charge, or enter a secret. Credentials must be
entered directly into the provider dashboard; never commit them to GitHub or
paste them into chat.

## Off-host backups

The application now creates and integrity-checks a local SQLite backup before
optionally uploading it to any S3-compatible object store. Set these Render
environment variables only after a bucket exists:

- `CARRIEROS_OFFSITE_BACKUP_BUCKET` — bucket name
- `CARRIEROS_OFFSITE_BACKUP_PREFIX` — normally `production`
- `CARRIEROS_OFFSITE_BACKUP_REGION` — provider region
- `CARRIEROS_OFFSITE_BACKUP_ENDPOINT` — leave blank for AWS S3; set for an S3-compatible provider
- `CARRIEROS_OFFSITE_BACKUP_SSE` — `AES256` by default, or `aws:kms`
- `CARRIEROS_OFFSITE_BACKUP_KMS_KEY_ID` — required only for a KMS key

Create an IAM/service account limited to writing and reading only the CarrierOS
backup prefix. Add its access key and secret through the provider's encrypted
secret store or Render environment settings. After deployment, confirm a new
object exists, has server-side encryption, and complete a restore rehearsal
from the off-host copy. The application still uses one SQLite instance until
the approved PostgreSQL migration is complete.

## Managed PostgreSQL

Choose a Render Postgres plan and approve its recurring cost. Do not switch the
production database URL until a restored production backup has been imported
into staging and table counts, tenant boundaries, and financial totals have
been reconciled. The cutover requires a maintenance window, a write freeze,
final backup, migration report, rollback owner, and human approval.

## SMTP

Choose a transactional email provider and verify the sender domain. Add the
following values in Render, not GitHub:

- `CARRIEROS_SMTP_HOST`
- `CARRIEROS_SMTP_PORT`
- `CARRIEROS_SMTP_SECURITY` (`starttls`, `ssl`, or `none`)
- `CARRIEROS_SMTP_AUTH_REQUIRED` (`true` unless the provider explicitly supplies an authenticated relay)
- `CARRIEROS_SMTP_USERNAME`
- `CARRIEROS_SMTP_PASSWORD`
- `CARRIEROS_SMTP_FROM`

After saving the variables, redeploy and request one password-reset email to a
controlled mailbox. Confirm delivery, the HTTPS link, 30-minute expiry, and
single-use behavior.

## Stripe lifecycle verification

Use Stripe test mode and a test clock for failed-payment and trial-ending
scenarios. For live mode, use one controlled CarrierOS account and a payment
method you own; do not use a customer’s card and do not paste card details into
chat. Record evidence for Checkout, signed webhooks, trial ending, paid invoice,
failed invoice, Customer Portal payment-method update, plan change, and
cancellation. Finish Stripe account review before paid marketing.

## Monitoring, legal, and security

The repository includes a scheduled readiness monitor that checks
`https://otwcarrieros.com/health/ready` every 15 minutes. Add a notification
destination for failures, then add provider-specific alerts for backup,
webhook, storage, and error-rate failures.

Counsel must review the Terms, Privacy Policy, trial/cancellation language,
refund terms, and document-data disclosures. An independent security reviewer
should assess authentication, tenant isolation, document uploads, secrets,
Stripe webhooks, backups, and incident response before accepting sensitive
customer records at scale.
