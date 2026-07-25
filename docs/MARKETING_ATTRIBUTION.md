# CarrierOS marketing attribution

CarrierOS preserves first-touch campaign information through account creation and
stores it with the new company record. Google Analytics receives only an
allowlist of campaign parameters; sensitive checkout and referral parameters are
not included in the reported page URL.

## Standard campaign names

Use lowercase words separated by underscores.

| Channel | Source | Medium | Campaign example |
| --- | --- | --- | --- |
| Founder email | `founder_email` | `email` | `purple_heart_founder_intro` |
| Customer newsletter | `customer_email` | `email` | `carrieros_product_update` |
| LinkedIn founder post | `linkedin` | `organic_social` | `small_fleet_profit_story` |
| LinkedIn direct outreach | `linkedin` | `direct_outreach` | `small_carrier_demo_invite` |
| Partner directory | partner name | `referral` | `carrier_software_directory` |
| Customer sharing link | `customer_dashboard` | `referral_link` | `spread_the_word` |
| Future Google Search campaign | `google` | `cpc` | the Google Ads campaign name |

Example founder-email URL:

`https://otwcarrieros.com/small-fleet-trucking-software?utm_source=founder_email&utm_medium=email&utm_campaign=purple_heart_founder_intro&utm_content=primary_demo_cta`

Do not add UTMs to links between CarrierOS pages. Internal UTMs overwrite useful
acquisition context in analytics systems.

## Conversion funnel

Review these events in order:

1. `view_demo`
2. `view_pricing`
3. `signup_cta_click`
4. `view_signup`
5. `begin_signup`
6. `signup_submit`
7. `sign_up`
8. `begin_checkout`
9. `checkout_handoff`
10. `trial_started`
11. `subscription_started`

`sign_up`, `trial_started`, and `subscription_started` are the primary business
conversions. Trial and paid-subscription events fire only after CarrierOS reflects
the verified billing state.

## Internal and launch testing

Open any CarrierOS page once with `?internal_test=1` to mark that browser's
subsequent analytics traffic as internal. Use `?internal_test=0` to remove the
marker. The GA4 internal-traffic data filter should remain in **Testing** mode
until the test audience is confirmed.

## Weekly scorecard

Track:

- attributable non-internal sessions;
- live-demo visitors;
- signup starts;
- completed accounts;
- verified trial starts;
- paid subscription starts;
- demo-to-trial and trial-to-paid conversion rates;
- conversion rate by source, medium, campaign, plan, and landing page.
