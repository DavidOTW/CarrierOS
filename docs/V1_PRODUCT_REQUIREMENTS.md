# CarrierOS V1 Product Requirements

Status: Phase 1 implemented in v0.13.0. Phase 2 and Phase 3 are planned and are not represented as complete.

## Product outcome

CarrierOS gives an owner-operator or small fleet a carrier-first operating workflow:

1. Receive a broker or customer offer.
2. Enter the offer without waiting for a RateCon.
3. Compare revenue with verified mileage, deadhead, fuel, driver pay, fixed cost, direct expense, and company thresholds.
4. Decide whether to book, negotiate, decline, or review.
5. Preserve the offer and negotiation history.
6. Convert an accepted opportunity exactly once to a booked load awaiting RateCon.
7. Continue through dispatch, settlement, billing, collections, and reporting in later phases.

RateCon is a post-agreement document. It is not a prerequisite for a pre-book profit check.

## Users

- Fleet owner: configures company thresholds, reviews profit, approves exceptions, and sees owner distribution.
- Dispatcher: enters offers quickly, compares drivers, negotiates, books, and follows the RateCon reminder.
- Office user: maintains driver/equipment records and sourced driver locations.
- Driver or contractor: represented by a pay profile. Direct driver self-service is deferred.

## Phase 1 functional requirements

### Rate Quote entry

- Required quick-entry fields: offered all-in rate, origin, destination, pickup, delivery, loaded miles.
- Optional pre-book driver selection. The user may compare all active drivers first.
- Advanced fields include ZIP codes, commodity, weight, pieces, stops, accessorial revenue, tolls, lumper, factoring, quick-pay fee, other direct expense, and service requirements.
- The original offered rate becomes immutable after creation.
- Editing an active opportunity creates a new immutable evaluation version.

### Profit Check

- Reuse the established CarrierOS driver-pay and cost formulas.
- Calculate total miles, deadhead percentage, revenue per loaded/total mile, fuel, maintenance, fixed cost, direct expenses, payroll burden, driver/contractor pay, owner-operator load pay, company profit, owner profit distribution, retained company profit, margin, profit per mile/day, and expected cash timing.
- Produce deterministic `BOOK`, `NEGOTIATE`, `DECLINE`, or `REVIEW REQUIRED` output.
- Give plain-language reasons and warnings.
- Calculate break-even, minimum acceptable rate, target rate, opening counteroffer, and maximum reasonable deadhead.
- Never present estimates as guaranteed profit, live GPS, legal compliance, or HOS availability.

### Driver comparison and location

- Compare each active driver's own pay profile.
- Use the most recent organization-scoped location record and preserve its source and timestamp.
- Fall back to the latest load destination as a clearly labeled projected location.
- Flag unknown or stale locations, overlapping scheduled loads, expired compliance records, and missing unit assignments.
- Use a routing-provider interface. Production defaults to manual mileage; a deterministic mock provider supports tests. A commercial routing integration is deferred.

### Negotiation and booking

- Store counteroffers, broker responses, notes, timestamps, and acting user in an append-only history.
- Provide a copyable negotiation message.
- Require a selected driver, active power unit, valid dates, final agreed rate, and positive loaded mileage to book.
- Require acknowledgement when review warnings remain.
- Create one operational load with status `Booked — Awaiting RateCon`.
- Preserve original offer and final agreed rate on both opportunity and load.
- Store separate immutable evaluation and booking snapshots.
- Prevent duplicate conversions at both application and database levels.

### Tenant isolation and onboarding

- Every operational query and mutation is constrained by `organization_id`.
- A new signup receives empty opportunity, load, driver, and financial records.
- OTW operating data is never seeded into customer organizations.
- Organization exports include opportunities, locations, histories, and snapshots.

## Non-functional requirements

- Browser-responsive desktop and mobile views.
- Server-side validation, production CSRF protection, secure signed sessions, audit events, and no credentials in source.
- SQLite single-replica deployment with persistent disk, backups, and verified restore practices until PostgreSQL migration.
- Backward-compatible `/quotes` calculator while customers transition to `/rate-quotes`.
- All existing workbook-parity and regression tests remain green.

## Deferred from Phase 1

- Commercial truck-routing/geocoding provider and market-rate data.
- RateCon upload, private object storage, document extraction, and document reconciliation.
- Driver GPS/ELD/HOS integrations.
- Tender execution, mobile driver portal, BOL/POD workflow, payroll remittance, invoicing automation, collections automation, and accounting sync.
- Team-based role permissions beyond the current organization administrator model.

## Phase 1 acceptance criteria

- A user can enter a valid offer and receive a deterministic result without a RateCon.
- Driver comparison changes deadhead and pay assumptions without re-entering the offer.
- Stale/unknown locations cannot appear authoritative.
- Booking creates exactly one load and stores two immutable calculation stages.
- A different organization cannot read, update, decline, or book the opportunity.
- Booked-load calculations pay the configured owner distribution percentage in addition to owner-operated load pay.
- Full automated suite passes.

