# CarrierOS v0.16 Role-Permission Matrix

Status: centralized policy implemented and unit-tested; route enforcement deferred.

| Capability | Owner | Administrator | Dispatcher | Accounting | Compliance | Read-only | Driver |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Dashboard view | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Quotes view/manage | ✓ | ✓ | ✓ | — | — | view | — |
| Loads view | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | assigned only |
| Loads manage | ✓ | ✓ | ✓ | — | — | — | status only |
| Dispatch approve | ✓ | ✓ | ✓ | — | — | — | acknowledge only |
| Money view/manage | ✓ | ✓ | — | ✓ | — | view | — |
| Invoices/payments/settlements manage | ✓ | ✓ | — | ✓ | — | — | own settlement view/respond |
| Compliance view/manage | ✓ | ✓ | — | — | ✓ | view | — |
| Operational documents | ✓ | ✓ | ✓ | — | ✓ | — | assigned upload |
| Financial documents | ✓ | ✓ | — | ✓ | — | — | — |
| Users, roles, billing, sensitive settings | ✓ | ✓* | — | — | — | — | — |

`*` Final policy should reserve ownership transfer, owner MFA recovery, destructive retention, and selected billing/security changes to Owner or require recent owner approval.

## Enforcement rules

- Use permission names, not inline role-name comparisons.
- Enforce server-side before loading the protected record.
- Apply organization ownership and permission checks independently.
- Driver access is additionally constrained to the authenticated driver's assigned record.
- UI visibility is convenience, never authorization.
- Permission changes generate audit events.
- Sensitive changes require recent reauthentication; Owner and Administrator require MFA before beta.

## PR 1 limitation

`app/permissions.py` is the tested single source of policy, but existing routes have not been migrated to it. No public or release claim may imply completed role enforcement until route-level and cross-tenant integration tests pass.
