# CarrierOS 0.16.0a20: workspace keyboard and form access

Baseline: production `/health` reported 0.16.0a19 on 2026-10-15; GitHub `main`
was `9191423`. The customer application is https://otwcarrieros.com. The
`carrieros-otw-logistics` ChatGPT Site is an older preview linking to that app.

## Change

- Connect visible labels to controls on new/edit load and rate-quote forms.
- Add a first-focusable skip link to workspace content after the mobile header.
- Give sidebar navigation an accessible landmark name and identify its current page.
- Correct simultaneous Money/Driver pay selection on the Driver pay page.
- Add visible keyboard focus indicators, with an inset, lighter sidebar outline.
- Advance the displayed release and static cache identifier together.

No calculation, schema, stored-record, access, billing, pricing, legal, or
entitlement changes. No production records were created for testing.

## Independent review

Claude reviewed sanitized source patterns against an explicit accessibility and
regression checklist:
https://claude.ai/chat/f5824694-4010-4378-a3aa-2bd30ba44c48

Applied its recommendations to target content after the header, keep sidebar
outlines inside the scroll area, and use the concise landmark name `Workspace`.
Verified that numeric-affix JavaScript moves the existing input node, keeps its
ID, and hides decorative affixes from assistive technology. Prefix routing was
already retained; native selects require no custom-widget adjustment. Retained
the native focus indicator on the skip destination for location feedback.

## Verification

- Existing suite passed before edits (127 tests).
- Regression check renders both entry forms, checks unique IDs and associated
  labels, and checks mutually exclusive Money/Driver pay navigation.
- Local rendered pages used only a fictional QA fleet and a separate SQLite file.
- Browser checks: label click focuses `load-revenue`; skip activation focuses
  content after `HEADER`; skip is first focusable element; 390px mobile layout
  stays in a single column. No form submissions to production.
- Ruff and Python compilation passed. The existing test tied to a hard-coded
  cache version now checks that the service worker matches the application release.

## Publication and rollback

Use the existing GitHub `main` to Render automatic deployment. Confirm the new
release through `/health` and the new stylesheet before reporting deployment.
No Squarespace link change is needed when it already points to otwcarrieros.com.

Rollback by reverting this release commit on `main` and redeploying, or selecting
the preceding successful Render deployment. Keep the persistent disk and all
runtime configuration unchanged. This release requires no schema rollback or
database restoration.
