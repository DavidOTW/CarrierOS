# Phase 1 Security Checklist

- [x] No passwords, Stripe secrets, SMTP passwords, or provider keys committed.
- [x] Production session secret length enforced.
- [x] Secure, HTTP-only, same-site production session cookies.
- [x] Production CSRF verification on new POST routes.
- [x] Subscription entitlement required for workspace access.
- [x] Organization scope on every new record read/write.
- [x] Active driver/unit ownership validated before booking.
- [x] Original/final rates stored separately.
- [x] Snapshot and negotiation tables enforced append-only by triggers.
- [x] Duplicate conversion blocked by transaction and unique index.
- [x] Customer export includes Phase 1 records.
- [x] Public robots rules block private Rate Quote paths.
- [x] Estimate, GPS/HOS, legal, and accounting limitations stated.
- [ ] Independent penetration test.
- [ ] Legal review of Terms/Privacy and commercial claims.
- [ ] Off-host restore drill using a recent production backup.
- [ ] PostgreSQL/row-level-security migration before multi-replica scale.
- [ ] Private object storage/security review before RateCon uploads.

