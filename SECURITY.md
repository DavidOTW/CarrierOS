# Security policy

CarrierOS separates every operational record by `organization_id`, uses versioned 600,000-iteration PBKDF2 password hashes with automatic legacy-hash upgrades, signs session cookies, enforces HTTPS-only cookies in production, validates production form tokens, throttles failed logins, account creation, and password resets, sends restrictive browser security headers, hashes new public onboarding tokens at rest, and records append-only account and password-recovery audit events.

This beta is not designed to store Social Security numbers, bank credentials, payment-card data, health records, or identity-document images. When paid subscriptions are enabled, payment details are collected and stored by Stripe rather than CarrierOS.

CarrierOS includes single-use, 30-minute password-reset links, but automated recovery is available only after a verified SMTP sender is configured. Before unattended paid sales, configure that sender, review Stripe entitlement automation in live mode, verify off-host backup restoration, formalize monitoring and incident response, and obtain an independent security review. Report vulnerabilities privately to the product owner rather than opening a public issue.
