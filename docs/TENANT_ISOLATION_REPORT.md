# Tenant Isolation Report

CarrierOS uses one database with mandatory `organization_id` ownership on all operational Phase 1 tables. Authenticated routes take the organization only from the signed session; no route accepts an organization identifier from the browser.

Verified controls:

- Opportunity list/detail/edit/negotiate/decline/book queries include the authenticated organization.
- Driver and vehicle selection requires a matching organization.
- Driver location writes and reads require the matching organization.
- Snapshots and negotiation history are read with both organization and opportunity IDs.
- Booking copies only tenant-owned driver/unit/opportunity data.
- Customer export selects each table by organization.
- New signups have zero opportunities and no OTW data.
- Automated cross-tenant detail access returns 404.

Residual risk: raw SQL requires continuing discipline. Before more engineering teams or public APIs are added, introduce repository methods or database row-level security with PostgreSQL and add policy tests for every new table.

