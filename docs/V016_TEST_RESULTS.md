# CarrierOS v0.16 PR 1 Test Results

Status: final local verification before draft pull request

Date: 2026-07-21

Branch: `agent/v016-architecture-data-integrity`

## Results

| Check | Exact result |
|---|---|
| Baseline before PR 1 | 56 passed |
| Final complete suite | 80 passed, 0 failed, 0 skipped |
| v0.16 foundation-focused tests | 24 passed |
| Coverage | 3,855 statements; 866 missed; **78% total** |
| Decimal quote module | 95% |
| Load state module | 94% |
| v0.16 migration module | 93% |
| Permissions module | 100% |
| Ruff static analysis | All checks passed across `app`, `scripts`, and `tests` |
| Python compile check | Passed for `app`, `scripts`, and `tests` |
| Dependency audit | 33 direct/transitive packages audited; 0 known vulnerabilities |
| Migration/rollback tests | Passed, including count/money parity, tenant checks, future normalized rows, immutable audit, and non-overwriting verified backups |
| Public-claims tests | Passed |

## Commands

```powershell
python -m ruff check app scripts tests
python -m coverage run --source=app -m pytest -q -p no:cacheprovider
python -m coverage report --show-missing
python -m compileall -q app scripts tests
python -m pip_audit -r requirements.txt --progress-spinner off --format json
python scripts/v016_inventory.py
```

## Known warning

The suite emits one Starlette deprecation warning because the current FastAPI test client compatibility layer uses legacy `httpx` behavior. It does not affect the results; dependency/API modernization should remove it in the hardening phase.

## Coverage interpretation

PR 1 adds reporting but no minimum threshold because the pre-existing application begins at 78%. A reviewed threshold should be introduced in the production-hardening PR and raised without excluding financial, tenant, billing, authentication, migration, or document-security code. Coverage is not evidence of closed-beta readiness by itself.

## Formatting baseline

Ruff lint is clean. A repository-wide Ruff formatting check identifies 29 legacy files that would be reformatted. PR 1 intentionally avoids a broad unrelated formatting diff; the formatting gate should be introduced in a dedicated governance change or PR 4 after the baseline is formatted and reviewed.

## Production evidence not claimed

These results use deterministic local SQLite fixtures and mocks. They do not demonstrate production PostgreSQL migration, private object storage, OCR/extraction, driver mobile workflows, invoice/settlement reconciliation, backup restoration from Render, Stripe live lifecycle, or independent security review.
