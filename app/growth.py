from __future__ import annotations

from typing import Any


STARTUP_STEPS: tuple[dict[str, str], ...] = (
    {
        "key": "operating_model",
        "category": "Business foundation",
        "title": "Define the operating model and 90-day cash plan",
        "summary": "Choose freight type, lanes, equipment, customer strategy, expected utilization, and the cash runway required before revenue becomes collectible.",
        "tutorial": "Build conservative low/base/high cases for revenue, fuel, insurance, maintenance, permits, dispatch, factoring, driver pay, and owner draws. Do not use gross revenue as spendable profit.",
        "action_label": "Model equipment economics",
        "action_url": "/growth",
    },
    {
        "key": "entity_ein",
        "category": "Business foundation",
        "title": "Form the entity, obtain an EIN, and separate business money",
        "summary": "Complete state formation first, then obtain an EIN directly from the IRS and open dedicated business banking and accounting records.",
        "tutorial": "Keep personal and carrier transactions separate from the beginning. Save formation records, EIN confirmation, ownership documents, and tax registrations in an approved secure system.",
        "action_label": "IRS EIN guidance",
        "action_url": "https://www.irs.gov/businesses/small-businesses-self-employed/get-an-employer-identification-number",
    },
    {
        "key": "registration_scope",
        "category": "Authority and registration",
        "title": "Determine USDOT and operating-authority requirements",
        "summary": "Classify the operation—private or for-hire, interstate or intrastate, property or passengers, cargo type, and vehicle weight—before applying.",
        "tutorial": "Use FMCSA's registration guidance for the actual operation. State requirements can apply in addition to federal registration, and not every startup needs the same authority.",
        "action_label": "FMCSA registration guide",
        "action_url": "https://www.fmcsa.dot.gov/registration/getting-started",
    },
    {
        "key": "motus_registration",
        "category": "Authority and registration",
        "title": "Complete the applicable FMCSA registration workflow",
        "summary": "Apply for the required USDOT number and operating authority through the current FMCSA registration system and protect the company official's login.",
        "tutorial": "Use the exact legal name and business contact information consistently. Track every application, fee, identity-verification step, and pending filing; avoid unofficial sites that imitate government registration.",
        "action_label": "FMCSA Motus information",
        "action_url": "https://www.fmcsa.dot.gov/registration/move-motus",
    },
    {
        "key": "insurance_boc3",
        "category": "Authority and registration",
        "title": "Arrange insurance filings and process-agent designation",
        "summary": "Confirm insurance limits and filings for the operation and complete BOC-3 when required before treating authority as active.",
        "tutorial": "Obtain written quotes using the real equipment, cargo, radius, driver history, and operation. Verify filings in FMCSA records; an insurance quote alone does not activate authority.",
        "action_label": "FMCSA filing requirements",
        "action_url": "https://www.fmcsa.dot.gov/registration/insurance-filing-requirements",
    },
    {
        "key": "ucr",
        "category": "Authority and registration",
        "title": "Determine and complete annual UCR registration",
        "summary": "Interstate motor carriers and certain other regulated transportation entities generally need annual UCR registration; use the official applicability tool.",
        "tutorial": "Confirm whether the operation is subject to UCR, register in the correct bracket, save the receipt, and calendar annual renewal. Intrastate-only operations may be treated differently.",
        "action_label": "Official UCR applicability tool",
        "action_url": "https://plan.ucr.gov/do-i-need-to-register/",
    },
    {
        "key": "irp_ifta",
        "category": "Vehicle and tax credentials",
        "title": "Determine IRP, IFTA, apportioned-plate, and state credential needs",
        "summary": "Equipment weight, jurisdictions traveled, base jurisdiction, and operation type determine which vehicle and fuel-tax credentials apply.",
        "tutorial": "Contact the base jurisdiction before operating. If IFTA applies, establish mileage and fuel-receipt controls before the first trip and calendar quarterly returns, including zero-activity returns when required.",
        "action_label": "IFTA carrier information",
        "action_url": "https://www.iftach.org/carriers/",
    },
    {
        "key": "equipment_readiness",
        "category": "Vehicle and tax credentials",
        "title": "Audit equipment, financing, inspection, and maintenance capacity",
        "summary": "Price the payment, insurance, registration, taxes, fuel, maintenance reserve, downtime, and replacement risk—not only the truck purchase price.",
        "tutorial": "Obtain an independent inspection and verify title, lien, warranty, maintenance history, emissions needs, tire/brake condition, and payload. Keep working capital after the down payment.",
        "action_label": "Run CarrierOS purchase audit",
        "action_url": "/growth",
    },
    {
        "key": "driver_compliance",
        "category": "Safety and drivers",
        "title": "Build driver qualification and drug/alcohol controls",
        "summary": "Determine CDL, driver-qualification, testing-program, Clearinghouse, and consortium/third-party administrator requirements before dispatching a driver.",
        "tutorial": "Owner-operators operating under their own authority may have both employer and driver obligations. Do not store Social Security numbers, test results, or Clearinghouse records in CarrierOS.",
        "action_label": "FMCSA owner-operator guidance",
        "action_url": "https://clearinghouse.fmcsa.dot.gov/Learn/Owner-Operator",
    },
    {
        "key": "new_entrant",
        "category": "Safety and drivers",
        "title": "Prepare for the New Entrant Safety Assurance Program",
        "summary": "Create auditable safety-management records before operations and understand the areas reviewed in a New Entrant safety audit.",
        "tutorial": "Assign responsibility for driver qualification, hours of service, maintenance, inspections, crashes, controlled substances, and record retention. Train everyone involved in daily operations.",
        "action_label": "FMCSA New Entrant training",
        "action_url": "https://www.fmcsa.dot.gov/carrier-safety/new-entrant/new-entrant-online-training",
    },
    {
        "key": "eld_hos",
        "category": "Safety and drivers",
        "title": "Select compliant logging, inspection, and safety workflows",
        "summary": "Determine hours-of-service and ELD applicability, daily vehicle-inspection processes, accident response, roadside-document access, and maintenance controls.",
        "tutorial": "Choose tools based on legal applicability and operational fit. Document training, exception handling, device failures, supporting documents, and escalation procedures.",
        "action_label": "FMCSA safety planner",
        "action_url": "https://csa.fmcsa.dot.gov/safetyplanner/",
    },
    {
        "key": "broker_credit",
        "category": "Freight and cash control",
        "title": "Create broker, shipper, and rate-confirmation controls",
        "summary": "Verify counterparties, payment terms, credit risk, accessorial rules, cargo requirements, and contact authenticity before accepting a load.",
        "tutorial": "Require a written RateCon, compare it with the booked terms, preserve revisions, verify payment instructions independently, and do not dispatch on an unexplained mismatch.",
        "action_label": "Open CarrierOS rate quotes",
        "action_url": "/rate-quotes",
    },
    {
        "key": "accounting_controls",
        "category": "Freight and cash control",
        "title": "Establish bookkeeping, document, and reconciliation routines",
        "summary": "Choose an accounting method and professional support, define the chart of accounts, and reconcile bank, card, fuel, payroll, settlements, loans, and receivables every month.",
        "tutorial": "CarrierOS estimates operating economics; it is not a general ledger or tax return. Use the audit screen to identify discrepancies, then resolve them in the accounting system.",
        "action_label": "Open document audits",
        "action_url": "/audits",
    },
    {
        "key": "launch_gate",
        "category": "Launch decision",
        "title": "Pass a documented launch gate before the first load",
        "summary": "Confirm active authority, insurance, credentials, safe equipment, qualified drivers, cash runway, communication, incident response, billing, and document retention.",
        "tutorial": "Have a qualified transportation attorney, insurance professional, tax/accounting professional, and safety consultant review the parts within their expertise. Delay launch when a critical control is incomplete.",
        "action_label": "Review CarrierOS dashboard",
        "action_url": "/dashboard",
    },
)


def equipment_finance_audit(values: dict[str, float], settings: dict[str, Any]) -> dict[str, Any]:
    price = max(0.0, values.get("purchase_price", 0.0))
    down = min(price, max(0.0, values.get("down_payment", 0.0)))
    financed = max(0.0, price - down)
    apr = max(0.0, values.get("apr_pct", 0.0)) / 100
    term = max(1, int(values.get("term_months", 60)))
    monthly_rate = apr / 12
    if financed <= 0:
        payment = 0.0
    elif monthly_rate <= 0:
        payment = financed / term
    else:
        payment = financed * monthly_rate * (1 + monthly_rate) ** term / ((1 + monthly_rate) ** term - 1)

    miles = max(0.0, values.get("monthly_miles", 0.0))
    revenue_per_mile = max(0.0, values.get("revenue_per_mile", 0.0))
    mpg = max(0.1, values.get("mpg", 8.0))
    diesel = max(0.0, values.get("diesel_price", 0.0))
    maintenance_per_mile = max(0.0, values.get("maintenance_per_mile", 0.0))
    driver_pct = min(90.0, max(0.0, values.get("driver_pay_pct", 0.0))) / 100
    insurance = max(0.0, values.get("monthly_insurance", 0.0))
    other_fixed = max(0.0, values.get("other_monthly_costs", 0.0))
    cash_reserve = max(0.0, values.get("cash_reserve", 0.0))

    revenue = miles * revenue_per_mile
    fuel = miles / mpg * diesel
    maintenance = miles * maintenance_per_mile
    driver_pay = revenue * driver_pct
    total_cost = payment + insurance + other_fixed + fuel + maintenance + driver_pay
    projected_profit = revenue - total_cost
    projected_margin = projected_profit / revenue if revenue else 0.0
    coverage_numerator = revenue - insurance - other_fixed - fuel - maintenance - driver_pay
    debt_service_coverage = coverage_numerator / payment if payment else None
    fixed_after_purchase = payment + insurance + other_fixed
    remaining_cash = cash_reserve - down
    reserve_months = remaining_cash / fixed_after_purchase if fixed_after_purchase else None
    variable_cost_per_mile = (diesel / mpg) + maintenance_per_mile
    contribution_fraction = max(0.01, 1 - driver_pct)
    break_even_rpm = (variable_cost_per_mile + (fixed_after_purchase / miles if miles else 0)) / contribution_fraction
    target_margin = float(settings.get("target_margin_pct") or 10.0) / 100.0

    findings: list[dict[str, str]] = []
    if miles <= 0 or revenue_per_mile <= 0:
        findings.append({"severity": "bad", "title": "Operating assumptions are incomplete", "detail": "Monthly miles and expected revenue per mile are required to test affordability."})
    elif projected_profit <= 0:
        findings.append({"severity": "bad", "title": "Projected monthly cash contribution is negative", "detail": "The scenario does not cover the payment, insurance, fuel, maintenance, other fixed costs, and entered driver-pay percentage."})
    elif projected_margin < target_margin:
        findings.append({"severity": "warn", "title": "Projected margin is below the company target", "detail": f"Scenario margin is {projected_margin:.1%}; CarrierOS target is {target_margin:.1%}."})
    else:
        findings.append({"severity": "good", "title": "Projected margin clears the current target", "detail": f"Scenario margin is {projected_margin:.1%} before taxes, unexpected downtime, and owner draws."})
    if debt_service_coverage is not None and debt_service_coverage < 1.25:
        findings.append({"severity": "bad", "title": "Thin payment coverage", "detail": f"Estimated operating cash before the truck payment covers debt service {debt_service_coverage:.2f} times; test lower utilization and revenue."})
    elif debt_service_coverage is not None:
        findings.append({"severity": "good", "title": "Modeled payment coverage", "detail": f"Estimated operating cash before the truck payment covers debt service {debt_service_coverage:.2f} times in the entered case."})
    if remaining_cash < 0:
        findings.append({"severity": "bad", "title": "Down payment exceeds cash reserve", "detail": "The scenario requires more cash than the entered reserve before registration, repairs, deposits, or working capital."})
    elif reserve_months is not None and reserve_months < 3:
        findings.append({"severity": "warn", "title": "Limited post-purchase fixed-cost runway", "detail": f"Remaining cash covers about {reserve_months:.1f} months of the new unit's payment, insurance, and other fixed costs."})
    else:
        findings.append({"severity": "good", "title": "Post-purchase reserve test", "detail": "The entered reserve leaves at least three months of the new unit's modeled fixed costs."})
    findings.append({"severity": "info", "title": "Run downside cases before signing", "detail": "Repeat the audit at lower miles and revenue, higher diesel and maintenance, and at least one month of downtime. Verify financing disclosures and obtain independent legal, tax, insurance, and mechanical review."})

    return {
        "financed_amount": financed,
        "monthly_payment": payment,
        "projected_revenue": revenue,
        "fuel_cost": fuel,
        "maintenance_cost": maintenance,
        "driver_pay": driver_pay,
        "total_cost": total_cost,
        "projected_profit": projected_profit,
        "projected_margin": projected_margin,
        "debt_service_coverage": debt_service_coverage,
        "remaining_cash": remaining_cash,
        "reserve_months": reserve_months,
        "break_even_rpm": break_even_rpm,
        "findings": findings,
    }


def growth_mentor_findings(summary: dict[str, Any], settings: dict[str, Any], active_units: int) -> list[dict[str, str]]:
    loads = int(summary.get("included_loads") or 0)
    revenue = float(summary.get("revenue") or 0)
    profit = float(summary.get("company_profit") or 0)
    margin = float(summary.get("company_margin_pct") or 0)
    target = float(settings.get("target_margin_pct") or 10.0) / 100.0
    findings: list[dict[str, str]] = []
    if loads == 0:
        findings.append({"severity": "warn", "title": "Build an operating baseline first", "detail": "CarrierOS has no included loads in the last 90 days, so it cannot compare a new-unit scenario with demonstrated fleet performance."})
        return findings
    findings.append({
        "severity": "good" if profit > 0 else "bad",
        "title": "Positive 90-day company profit" if profit > 0 else "Negative 90-day company profit",
        "detail": f"{loads} included loads produced ${revenue:,.2f} of revenue and ${profit:,.2f} of company profit before owner distribution.",
    })
    findings.append({
        "severity": "good" if margin >= target else "warn",
        "title": "Historical margin clears target" if margin >= target else "Historical margin is below target",
        "detail": f"The 90-day company margin is {margin:.1%} against the configured {target:.1%} target.",
    })
    if active_units:
        findings.append({
            "severity": "info", "title": "Scale from demonstrated unit economics",
            "detail": f"Revenue averaged ${revenue / active_units:,.2f} per active unit across the selected 90-day window. Confirm that the proposed unit has freight, a qualified driver, and working capital rather than assuming fleet averages will repeat.",
        })
    return findings
