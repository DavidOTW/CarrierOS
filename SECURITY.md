# Security policy

CarrierOS public beta separates every operational record by `organization_id`, uses salted PBKDF2 password hashes, signs session cookies, enforces HTTPS-only cookies in production, validates production form tokens, throttles failed logins and account creation, sends restrictive browser security headers, and records append-only account creation, login, and logout audit events.

This beta is not designed to store Social Security numbers, bank credentials, payment-card data, health records, or identity-document images. When paid subscriptions are enabled, payment details are collected and stored by Stripe rather than CarrierOS.

Founding-beta password recovery is handled manually through the published support address. Before unattended paid sales, add verified email delivery and self-service recovery, review the existing Stripe entitlement automation in test mode, verify off-host backup restoration, formalize monitoring and incident response, and obtain an independent security review. Report vulnerabilities privately to the product owner rather than opening a public issue.
