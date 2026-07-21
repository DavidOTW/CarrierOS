# CarrierOS public beta

CarrierOS is a multi-company fleet financial workspace for small carriers. Each signup receives an empty, isolated organization with a 14-day trial and an active-power-unit limit based on the selected plan. The launch configuration uses a no-charge founding beta; Stripe Billing can be enabled later without changing the account model.

## Included in this release candidate

- Customer signup with versioned terms consent, sign-in, secure sessions, production CSRF checks, account throttling, security headers, and an append-only account audit trail
- Organization-scoped loads, units, drivers, payments, fuel, quoting, financials, compliance, onboarding, documents, detention, and receivables
- Seven driver-pay structures: profit split, contractor gross split, owner-operator split, flat rate per load, loaded-mile rate, total-mile rate, and day rate
- Plans for 2, 10, and 25 active power units at $19, $49, and $99 per month
- No-charge beta access plus Stripe-hosted subscription Checkout, Customer Portal, and webhook-driven entitlements for the later paid launch
- Docker packaging with a non-root process, dynamic platform port, health check, and persistent data volume
- Public Privacy Policy and Terms of Service pages

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

Copy `.env.example` to `.env`, generate a unique `CARRIEROS_SECRET` of at least 32 characters, and set the public HTTPS application URL. Keep `CARRIEROS_BILLING_MODE=beta` for the no-charge founding beta. To test paid billing later, switch the mode to `stripe` and add test-mode Stripe secrets and Price IDs through the host's secret manager. Never commit a real Stripe key or webhook signing secret.

```powershell
docker compose up --build -d
```

The HTTPS reverse proxy or hosting platform must terminate TLS. Back up the persistent `/data` volume. SQLite requires a single application replica; migrate to a managed transactional database before horizontal scaling.

### Render deployment

`render.yaml` defines a single Starter web service with a 1 GB persistent disk mounted at `/data`, a generated production session secret, beta billing mode, and a health check. Create a Render Blueprint from this repository and review the displayed recurring price before applying it. Do not remove the persistent disk or scale the SQLite service above one instance.

## Billing architecture

Squarespace remains the marketing site. During the founding beta, plan links should send customers directly to CarrierOS signup and no payment method is collected. When `CARRIEROS_BILLING_MODE=stripe`, the application associates the authenticated organization with a server-created Stripe Checkout Session. Stripe Billing then becomes the subscription system of record. CarrierOS grants or removes paid access only after signature-verified, idempotently processed Stripe webhooks; the Checkout success redirect never grants access.

Configure a Stripe webhook endpoint at `https://YOUR-APP/stripe/webhook` for `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `customer.subscription.trial_will_end`, `invoice.paid`, and `invoice.payment_failed`. The three standard monthly Price IDs must be supplied through the corresponding `STRIPE_PRICE_*` environment variables. Configure the Stripe Customer Portal to allow the plan changes and cancellation behavior you intend to support.

Stripe Connect is intentionally not part of the initial SaaS billing release. Calculating contractor compensation does not by itself justify Connect, and Connect must not be treated as a general payroll or arbitrary payout service. Reassess Connect when CarrierOS has a defined underlying customer-to-fleet or customer-to-contractor payment flow.

## Go-live checklist

- Deploy the Docker image to an HTTPS host with persistent storage, platform health monitoring, and daily backups.
- Keep the app on one instance, set the support email, and use a generated strong session secret in host-managed environment variables.
- Review the included Privacy Policy and Terms of Service with a qualified attorney before paid sales.
- Add verified email delivery and self-service password reset before unattended paid sales; beta account recovery is handled manually through support.
- Before enabling `stripe` mode, create the three recurring Stripe Prices in test mode, configure the Customer Portal, and test every subscription lifecycle event.
- Run an independent security review before storing regulated or highly sensitive data.

CarrierOS operational and document outputs require professional review. Do not enter Social Security numbers, banking credentials, or identity-document images in this beta.
