# CarrierOS v0.13.0 — Phase 1 Release Notes

## Added

- Persistent Rate Quotes that start with the broker/customer offer.
- Quick-entry and advanced offer fields.
- Profit Check with deterministic booking recommendation and reasons.
- Minimum acceptable rate, opening counteroffer, deadhead limit, cash need, and expected payment timing.
- Driver comparison using each saved pay profile and sourced location.
- Stale/unknown location, schedule conflict, expired compliance, and missing-unit warnings.
- Negotiation history and copyable message.
- Exactly-once booking to `Booked — Awaiting RateCon`.
- Immutable evaluation and booking snapshots.
- Owner profit distribution shown separately from owner-operated load pay.
- Settings for profit, margin, revenue, counteroffer, location freshness, RateCon reminder, and payment timing thresholds.

## Changed

- Primary navigation now follows the carrier workflow: Today, Rate Quotes, Loads, Money, Drivers & Equipment, Compliance, Reports, Connections, Settings.
- Public copy now correctly starts the workflow at the offer/profit check rather than the RateCon.
- Database schema upgraded from version 9 to 10.
- PWA cache version upgraded to v0.13.0.

## Compatibility

- The earlier `/quotes` calculator remains available.
- Existing loads and financial calculations are unchanged.
- The migration is additive and idempotent.

## Not included

Commercial routing, RateCon file processing, market-rate data, ELD/HOS, driver mobile workflow, automated settlement/invoicing, and accounting sync remain future phases.

