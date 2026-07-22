# CarrierOS

CarrierOS is a multi-company fleet financial workspace for small carriers. Each signup receives an empty, isolated organization with a 14-day Stripe subscription trial and an active-power-unit limit based on the selected plan.

## v0.16 review status

Phase 3 is deployed on `main` as **v0.16.0a3**. The Phase 4 branch is **v0.16.0a4** and adds the first production beta hardening slice: a non-mutating release-readiness gate with live billing, secure storage, managed malware scanning, database integrity, and verified-backup checks. It remains a draft until reviewed and promoted.

The deployed `main` branch contains **v0.16.0a2, PR 2 — RateCon to Dispatch**. The current development branch is **v0.16.0a3, PR 3 — Delivery to Cash (first slice)**. Phase 2 is live with safe retained-document boundaries, evidence-bearing human review, candidate matching, material-difference approval, ranked driver/equipment assignment, dispatch approval, and a single-load driver acknowledgment page.

Production RateCon upload refuses to run until encrypted private storage is explicitly configured; dispatch remains blocked until a malware scanner returns `CLEAN`. The protected legacy calculation path remains customer-facing while Phase 2 stores separate booking and RateCon-confirmed snapshots. The Phase 3 draft adds controlled pickup/transit/delivery status updates and private BOL/POD/receipt/detention-evidence uploads from the driver dispatch link, with office review surfaces. Invoice packets, payment ledgers, versioned settlements, managed PostgreSQL, background processing, MFA, and production beta hardening remain subsequent Phase 3/4 work. See `docs/PHASE2_RATECON_DISPATCH.md`, `docs/PHASE3_DELIVERY_TO_CASH.md`, and the v0.16 architecture, migration, threat, rollback, and test documents.

## Included in this release candidate

- Phase 1 carrier workflow: broker/customer offer, pre-book profit check, driver comparison, negotiation history, and exactly-once conversion to `Booked — Awaiting RateCon`
- On the deployed release: manually verified RateCon dispatch details with driver-ready SMS composition, pickup/delivery appointment windows, contacts, instructions, and Apple/Google navigation links
- Deterministic `BOOK`, `NEGOTIATE`, `DECLINE`, and `REVIEW REQUIRED` recommendations based on company margin, profit, profit-per-mile/day, revenue-per-mile, and deadhead thresholds
- Immutable evaluation/booking snapshots that preserve the original offer, final rate, company settings, and selected driver pay profile
- Sourced and timestamped driver locations with stale/unknown warnings and a routing-provider boundary; production uses manually verified mileage until a commercial provider is configured
- Customer signup with versioned terms consent, sign-in, secure sessions, production CSRF checks, account throttling, security headers, self-service password reset when SMTP is configured, and an append-only account audit trail
- Organization-scoped loads, units, drivers, payments, fuel, quoting, financials, compliance, onboarding, documents, detention, and receivables
- Privacy-first document audits for text-based RateCon PDFs, business-bank PDF/CSV exports, and bill PDFs; raw uploads are discarded after structured findings and a checksum are produced
- A carrier-startup checklist with official-source tutorials plus equipment purchase/finance scenario mentoring
- Seven driver-pay structures: profit split, contractor gross split, owner-operator split, flat rate per load, loaded-mile rate, total-mile rate, and day rate
- A $10/month pre-authority startup plan with zero active units, plus plans for 2, 5, 10, and 20 active power units at $25, $50, $75, and $100 per month
- Stripe-hosted subscription Checkout, Customer Portal, webhook-driven entitlements, and a card-on-file 14-day trial
- Docker packaging with a non-root process, dynamic platform port, health check, and persistent data volume
- Daily consistent SQLite backups with retention, Render disk snapshots, and authenticated company-data export
- Public Privacy Policy and Terms of Service pages

The earlier V1 roadmap and Phase 1 boundary remain in `docs/V1_PRODUCT_REQUIREMENTS.md`, `docs/V1_ARCHITECTURE.md`, `docs/V1_IMPLEMENTATION_PLAN.md`, and `docs/V1_RISK_REGISTER.md`; the v0.16 documents above are authoritative for the current four-PR program. Commercial routing, production OCR, live GPS/ELD/HOS, automated SMS delivery, invoice/payment automation, settlement approval, collections, and accounting sync are not available in the deployed v0.16.0a2 application. Phase 2 extraction and Phase 3 delivery documents propose facts for human review; they do not make financial decisions or provide accounting advice.

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/signup`. The application creates a new local SQLite database and does not include sample customer data or default credentials.

## Tests

```powershell
python -m pytest
python -m compileall -q app scripts tests
python -m ruff check app scripts tests
python -m coverage run --source=app -m pytest -q
python -m coverage report --show-missing
python -m pip_audit
python scripts/v016_inventory.py
```

## Production configuration

Copy `.env.example` to `.env`, generate a unique `CARRIEROS_SECRET` of at least 32 characters, and set the public HTTPS application URL. Use test-mode Stripe secrets and Price IDs until the full lifecycle passes. In production, CarrierOS automatically closes signup and Checkout when the configured Stripe key is not live, preventing a customer from reaching test-mode billing. Never commit a real Stripe key or webhook signing secret.

```powershell
docker compose up --build -d
```

The HTTPS reverse proxy or hosting platform must terminate TLS. CarrierOS creates consistent SQLite backups in `CARRIEROS_BACKUP_DIR` every 24 hours and keeps the latest 14 by default. Render also snapshots the persistent disk daily. Copy logical backups off-host and test restoration regularly. SQLite requires a single application replica; migrate to a managed transactional database before horizontal scaling.

### Render deployment

`render.yaml` defines a single Starter web service with a 1 GB persistent disk mounted at `/data`, automated logical-backup settings, a generated production session secret, Stripe billing mode, required secret placeholders, the public application URL, and a health check. Create a Render Blueprint from this repository and review the displayed recurring price before applying it. Do not remove the persistent disk or scale the SQLite service above one instance.

## Billing architecture

Squarespace remains the marketing site and sends plan links directly to CarrierOS signup; it does not create a second Squarespace Commerce subscription. CarrierOS associates the authenticated organization with a server-created Stripe Checkout Session. Stripe Billing is the subscription system of record. CarrierOS grants or removes paid access only after signature-verified, idempotently processed Stripe webhooks; the Checkout success redirect never grants access. Before every Checkout Session, CarrierOS retrieves the configured Stripe Price and refuses checkout unless its active status, USD amount, monthly recurrence, and licensed billing model match the selected CarrierOS plan.

Configure a Stripe webhook endpoint at `https://YOUR-APP/stripe/webhook` for `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `customer.subscription.trial_will_end`, `invoice.paid`, and `invoice.payment_failed`. The five standard monthly Price IDs must be supplied through the corresponding `STRIPE_PRICE_*` environment variables. Configure the Stripe Customer Portal to allow the plan changes and cancellation behavior you intend to support.

Stripe Connect is intentionally not part of the initial SaaS billing release. Calculating contractor compensation does not by itself justify Connect, and Connect must not be treated as a general payroll or arbitrary payout service. Reassess Connect when CarrierOS has a defined underlying customer-to-fleet or customer-to-contractor payment flow.

Set `CARRIEROS_ROUTE_PROVIDER=manual` in production. The included `estimated` adapter is a clearly labeled non-commercial development estimate and is not appropriate for booking decisions. Automated tests use the deterministic mock adapter.

### Phase 2 document controls

Set `CARRIEROS_PRIVATE_STORAGE_ROOT` to a non-public persistent location. Production upload additionally requires `CARRIEROS_STORAGE_ENCRYPTED_AT_REST=true`; this is an operator assertion that the managed volume or object store supplies encryption at rest. Set `CARRIEROS_MALWARE_SCANNER` only to a configured scanner adapter. The default `manual` scanner cannot advance a document to dispatch. Automated tests use private in-memory storage and deterministic malware/OCR/extraction mocks; they call no production provider.

## Go-live checklist

- Deploy the Docker image to an HTTPS host with persistent storage, platform health monitoring, daily logical backups, and tested off-host restoration.
- Keep the app on one instance, set the support email, and use a generated strong session secret in host-managed environment variables.
- Review the included Privacy Policy and Terms of Service with a qualified attorney before paid sales.
- Configure a verified SMTP sender so the included single-use, 30-minute password-reset flow can deliver email. Until then, recovery falls back to the published support address.
- Before replacing test credentials with live credentials, create the five recurring Stripe Prices in live mode, configure the Customer Portal, and test every subscription lifecycle event.
- Run an independent security review before storing regulated or highly sensitive data, and move to managed PostgreSQL before horizontal scaling or higher-availability requirements.

CarrierOS operational, startup, audit, and growth outputs require professional review. Uploaded audit documents are processed in memory and discarded, but filenames, checksums, extracted figures, and findings are retained in the company workspace. Do not upload or enter Social Security numbers, banking credentials, full account numbers, tax IDs, or identity-document images.
