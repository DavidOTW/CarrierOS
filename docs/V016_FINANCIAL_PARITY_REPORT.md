# CarrierOS v0.16 Financial Parity Report

Status: PR 1 foundation evidence; Decimal path is **not** authoritative.

## Protected baseline

The v0.15 calculation engine was executed before the Decimal implementation was added. Its expected outputs were frozen in `tests/fixtures/v016_quote_golden.json`. The fixture covers all seven backend pay models and includes company fees, operating expense, fuel, maintenance, fixed cost, driver/contractor pay, owner-operator pay, company profit, recommended minimum revenue, and decision.

## Comparison result

`tests/test_v016_money_foundation.py` runs the protected legacy function and the side-by-side Decimal function from the same input for:

1. Profit Split
2. Contractor Gross Split
3. Owner-Operator
4. Flat Rate per Load
5. Per Loaded Mile
6. Per Total Mile
7. Day Rate

Each currency field must equal the frozen fixture and the other implementation to `0.01`; the recommendation must match exactly. The PR 1 targeted suite passes all cases. Strict-input tests additionally prove malformed numeric text is rejected by the Decimal path rather than silently becoming zero.

## Rounding policy

- Currency quantum: `0.01`.
- Rate quantum: `0.000001`.
- Percentage quantum: `0.0001`.
- Rounding: `ROUND_HALF_UP`.
- New persistence representation: currency cents, rate micros, and percentage basis points.

## Historical protection

The existing customer routes still use the protected legacy calculation engine. The migration copies values into additive normalized records but does not replace or recalculate legacy history. New `load_financial_snapshots` are append-only and carry calculation version plus rounding policy.

## Known evidence gap

The user-provided OTW workbook was located but not modified. The required workbook artifact runtime was unavailable, so direct extraction of fresh workbook fixtures was blocked. Substituting an unapproved spreadsheet library would violate the required artifact workflow. Existing protected outputs are therefore the PR 1 evidence; direct workbook-derived fixtures remain mandatory before activation.

## Activation decision

**No-go for switching customer calculations.** Activation requires:

- artifact-reviewed OTW workbook fixtures;
- reconciliation of historical OTW records and five beta-carrier pay configurations;
- reviewed differences, if any;
- dual-run reporting on migrated data;
- immutable snapshot coverage;
- explicit owner/financial reviewer approval.
