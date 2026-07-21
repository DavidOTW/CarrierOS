# Phase 1 Test Results

Date: 2026-07-21

- Pre-change baseline: 44 passed.
- Phase 1 targeted suite: 5 passed.
- Final full regression suite: 48 passed.
- Python compilation: passed.
- Known warning: Starlette reports that its current `httpx` TestClient compatibility layer is deprecated. This does not fail runtime or tests; dependency modernization is tracked.

Phase 1 tests cover:

- manual quote profitability and deterministic recommendation;
- owner profit distribution plus retained company profit;
- driver comparison and provider-sourced deadhead;
- stale driver location warning;
- new-customer empty workspace;
- tenant-isolated quote access;
- quote-to-load conversion;
- original/final rate preservation;
- RateCon-pending status;
- duplicate booking prevention;
- immutable snapshot database enforcement;
- production schema migration to version 10.

The broader suite covers workbook parity, seven pay models, owner/driver balances, load filters/reports, record editing/voiding, signup/subscriptions, Stripe billing/webhooks, public SEO/demo pages, backup/export, authentication, and deployment readiness.

