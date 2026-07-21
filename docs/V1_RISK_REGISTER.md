# CarrierOS V1 Risk Register

| ID | Risk | Likelihood | Impact | Current mitigation | Next action |
|---|---|---:|---:|---|---|
| R1 | Manual or stale mileage creates a misleading quote | Medium | High | Mileage source is labeled; unknown/stale location forces review; production routing provider defaults to manual | Add commercial truck routing and route-version snapshots |
| R2 | Driver availability is mistaken for live HOS/GPS status | Medium | High | UI explicitly disclaims live GPS/HOS; schedule conflict is only an internal load check | Integrate consented ELD/telematics provider with freshness metadata |
| R3 | A booking is duplicated | Low | High | Transaction check, unique `booked_load_id`, and partial unique load index | Use PostgreSQL row locking before multi-replica scale |
| R4 | Historical quote math changes after settings/pay edits | Low | High | Immutable snapshot stores opportunity, thresholds, driver pay profile, and result | Add cryptographic snapshot checksum in Phase 2 |
| R5 | Tenant data leaks across companies | Low | Critical | Organization-scoped routes/queries, tenant tests, blank signup, tenant export boundaries | Add automated query policy/lint and independent penetration test |
| R6 | SQLite concurrency or disk failure | Medium | Critical | One replica, persistent disk, WAL, logical backups, Render snapshots | Test off-host restoration and migrate to managed PostgreSQL before scale |
| R7 | RateCon/document data is stored insecurely | Not applicable in Phase 1 | Critical | Phase 1 does not accept RateCon files | Private object storage, scanning, encryption, retention policy before Phase 2 |
| R8 | Recommendation is treated as guaranteed profitability | Medium | High | Deterministic reasons, estimate language, warnings, Terms disclaimers | Add per-quote acknowledgement and training content |
| R9 | Company thresholds are configured poorly | Medium | Medium | Defaults plus visible Settings controls and explanations | Guided setup and threshold validation ranges |
| R10 | Owner distribution is confused with owner-operated load pay | Medium | High | UI and engine display them separately; booked-load engine pays both where applicable | Add settlement-specific owner statement in Phase 3 |
| R11 | Credentials or API keys enter source/history | Low | Critical | Environment variables and ignored `.env`; no new credential requirements | Secret scanning and rotation runbook |
| R12 | The monolithic route module slows future changes | High | Medium | Calculation and routing logic moved to dedicated modules | Split auth, billing, opportunities, loads, and reports into routers |
| R13 | Append-only triggers interfere with tenant deletion | Medium | Medium | No hard-delete customer workflow is exposed | Design retention-compliant archival/deletion procedure before adding account deletion |
| R14 | Public marketing overstates unfinished features | Medium | High | Phase 1 copy is limited to implemented profit checks and existing functions | Review public claims at every release gate |

