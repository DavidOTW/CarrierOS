# CarrierOS v0.16 Public-Claims Audit

## Rule

Public copy describes only behavior available in the current application and clearly labels estimates, fictional samples, manual fallbacks, and professional-review boundaries. Route names retained for SEO continuity do not override visible accuracy.

## Corrections in PR 1

| Prior implication | Correction |
|---|---|
| A RateCon begins the profit decision | A broker offer begins the pre-book profit decision |
| Seven methods included hourly and salary | Exact backend models: profit split, contractor gross split, owner-operator split, flat per load, loaded mile, total mile, day rate |
| Fictional dashboard was a “real-time view” | Labeled “fictional sample” |
| Sample driver settlement was approved | Labeled estimated driver pay; no approval claim |
| Settlement workflow was available | Visible copy describes driver-pay estimation and payment tracking |
| Profit figures appeared definitive | SEO and demo identify estimated results and user-entered assumptions |

## Existing boundaries retained

- CarrierOS is not payroll, accounting, tax, legal, insurance, or regulatory advice.
- Limited text-based document audits are discrepancy screens; no general-ledger reconciliation is claimed.
- Raw uploaded audit documents are currently discarded; OCR/private retained storage are not claimed.
- Manual routing remains the production fallback; no live GPS, ELD, HOS, or authoritative straight-line mileage claim is permitted.
- Automated settlement approval, invoice packet completion, collections, and accounting sync remain deferred.

## Automated guard

`tests/test_v016_public_claims.py` verifies the public templates contain the seven supported pay labels, omit hourly/salary claims, label fictional data, and do not present an approved sample settlement or real-time dashboard. Route tests verify the corrected SEO title and demo content.

Later PRs must expand this guard for RateCon extraction, routing/HOS, document storage, reconciliation, guaranteed profitability/compliance, invoice, and settlement claims as those surfaces are introduced.

## Result

**Pass for the reviewed public marketing/demo/SEO surfaces in PR 1.** The broader app copy inventory remains executable through `python scripts/v016_inventory.py` and must be reviewed in each phase.
