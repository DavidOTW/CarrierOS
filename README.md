# CarrierOS public beta

CarrierOS is a multi-company fleet financial workspace for small carriers. Each signup receives an empty, isolated organization with a 14-day trial and an active-power-unit limit based on the selected plan.

## Included in this release candidate

- Customer signup, sign-in, secure sessions, production CSRF checks, login throttling, and security headers
- Organization-scoped loads, units, drivers, payments, fuel, quoting, financials, compliance, onboarding, documents, detention, and receivables
- Seven driver-pay structures: profit split, contractor gross split, owner-operator split, flat rate per load, loaded-mile rate, total-mile rate, and day rate
- Plans for 2, 10, and 25 active power units at $19, $49, and $99 per month
- Stripe-hosted subscription Checkout, 14-day card-on-file trials, Customer Portal, and webhook-driven entitlements
- Docker packaging with a non-root process, health check, and persistent data volume

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/signup`. The application creates a new local SQLite database and does not include sample customer data or default credentials.

## Tests

```powershell
python -m pytest
```

## Production configuration

Copy `.env.example` to `.env`, generate a unique `CARRIEROS_SECRET` of at least 32 characters, set the public HTTPS application URL, and add test-mode Stripe secrets and Price IDs through the host's secret manager. Never commit a real Stripe key or webhook signing secret.

```powershell
docker compose up --build -d
```

The HTTPS reverse proxy or hosting platform must terminate TLS. Back up the persistent `/data` volume. SQLite requires a single application replica; migrate to a managed transactional database before horizontal scaling.

## Billing architecture

Squarespace remains the marketing site. Plan links should send customers to CarrierOS signup so the application can associate the authenticated organization with a server-created Stripe Checkout Session. Stripe Billing is the subscription system of record. CarrierOS grants or removes access only after signature-verified, idempotently processed Stripe webhooks; the Checkout success redirect never grants access.

Configure a Stripe webhook endpoint at `https://YOUR-APP/stripe/webhook` for `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `customer.subscription.trial_will_end`, `invoice.paid`, and `invoice.payment_failed`. The three standard monthly Price IDs must be supplied through the corresponding `STRIPE_PRICE_*` environment variables. Configure the Stripe Customer Portal to allow the plan changes and cancellation behavior you intend to support.

Stripe Connect is intentionally not part of the initial SaaS billing release. Calculating contractor compensation does not by itself justify Connect, and Connect must not be treated as a general payroll or arbitrary payout service. Reassess Connect when CarrierOS has a defined underlying customer-to-fleet or customer-to-contractor payment flow.

## Go-live checklist

- Create the three recurring Stripe Prices in test mode, configure the Customer Portal, and test every subscription lifecycle event.
- Deploy the Docker image to an HTTPS host with persistent storage and daily backups.
- Set the Stripe secrets, Price IDs, public URL, and strong session secret in host-managed environment variables.
- Add password-reset email, immutable audit logging, monitoring, and a written privacy policy/terms before unattended public sales.
- Run an independent security review before storing regulated or highly sensitive data.

CarrierOS operational and document outputs require professional review. Do not enter Social Security numbers, banking credentials, or identity-document images in this beta.
