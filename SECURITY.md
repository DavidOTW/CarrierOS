# Security policy

CarrierOS public beta separates every operational record by `organization_id`, uses salted PBKDF2 password hashes, signs session cookies, enforces HTTPS-only cookies in production, validates production form tokens, throttles failed logins, and sends restrictive browser security headers.

This beta is not designed to store Social Security numbers, bank credentials, payment-card data, or identity-document images. Payment details belong in Squarespace Payments.

Before accepting unattended public customers, add password-reset email, automated billing entitlements, immutable audit logs, tested off-host backups, monitoring, incident response, and an independent security review. Report vulnerabilities privately to the product owner rather than opening a public issue.
