"""Public, version-controlled operating guides for the CarrierOS workspace."""

from __future__ import annotations

from typing import Any


HELP_GROUPS = (
    {
        "key": "daily",
        "title": "Daily workflow",
        "summary": "Quote, book, dispatch, deliver, and understand the money on each load.",
    },
    {
        "key": "review",
        "title": "Review and tools",
        "summary": "Maintain the records, controls, and decision-support tools around the fleet.",
    },
    {
        "key": "admin",
        "title": "Administration",
        "summary": "Configure the company workspace, users, subscription, and optional programs.",
    },
)


_GUIDES: tuple[dict[str, Any], ...] = (
    {
        "slug": "dashboard",
        "group": "daily",
        "icon": "DB",
        "title": "Dashboard",
        "route": "/dashboard",
        "summary": "Read the fleet's operating picture and move quickly to the records needing attention.",
        "purpose": (
            "Dashboard is the opening command center. It summarizes included-load revenue, "
            "company profit, unpaid driver balances, active loads, availability, receivables, "
            "and model or compliance exceptions."
        ),
        "steps": (
            "Review the four headline metrics for revenue, company profit, unpaid driver balance, and open exceptions.",
            "Scan Loads in motion for current status, assigned driver and unit, revenue, profit, and the model decision.",
            "Use Driver and unit availability to see the next open date and last booked destination recorded in CarrierOS.",
            "Open Model alerts and receivables when a count or balance needs attention.",
            "Use Add load, Quote a lane, or the panel links to continue the workflow.",
        ),
        "key_points": (
            ("Included loads", "Dashboard totals use loads marked for inclusion in the financial model."),
            ("Availability", "Dates and locations come from CarrierOS records, not live GPS, ELD, or HOS data."),
            ("Balances", "Earned amounts are reduced only by payments and adjustments recorded in the workspace."),
        ),
        "tips": (
            "Treat Dashboard as a review screen; correct the underlying load, payment, compliance item, or setting rather than trying to edit a total.",
            "Investigate exceptions before relying on a margin or unpaid-balance number.",
        ),
        "related": ("loads", "money", "dispatch"),
    },
    {
        "slug": "dispatch",
        "group": "daily",
        "icon": "DS",
        "title": "Dispatch",
        "route": "/dispatch",
        "summary": "Plan current movements and open the controlled assignment workflow for a load.",
        "purpose": (
            "Dispatch brings scheduled loads, appointment dates, drivers, units, and operating "
            "status together. It is the starting point for assigning an approved RateCon load "
            "and preparing the driver acknowledgment."
        ),
        "steps": (
            "Review the dispatch board for loads that are planned, assigned, moving, or awaiting action.",
            "Open the selected load and confirm that its RateCon review is complete before assignment.",
            "Compare the ranked driver, power-unit, and trailer candidates and independently verify HOS availability.",
            "Approve the assignment, review the recalculated profitability, and complete the final dispatch approval.",
            "Send the secure acknowledgment link to the assigned driver and monitor the recorded delivery status.",
        ),
        "key_points": (
            ("Assignment gate", "Dispatch cannot advance until required RateCon review and safety checks are complete."),
            ("Driver link", "The signed link exposes only the assigned trip details and permitted delivery actions."),
            ("Live status", "CarrierOS is not a live GPS, ELD, HOS, or automated messaging service."),
        ),
        "tips": (
            "Verify appointment windows, time zones, addresses, contacts, and instructions before approval.",
            "Do not treat a ranking as a substitute for the dispatcher and driver's safety judgment.",
        ),
        "related": ("ratecon-inbox", "loads", "drivers-equipment"),
    },
    {
        "slug": "rate-quotes",
        "group": "daily",
        "icon": "RQ",
        "title": "Rate quotes",
        "route": "/rate-quotes",
        "summary": "Test a broker or customer offer against real operating assumptions before booking.",
        "purpose": (
            "Rate quotes estimates revenue, fuel, driver pay, equipment cost, deadhead, and "
            "company margin before the carrier accepts an offer. It also preserves the "
            "negotiation and booking decision."
        ),
        "steps": (
            "Choose New rate quote and enter the customer or broker, lane, dates, offered rate, miles, and known load costs.",
            "Confirm the route source and mileage; production decisions should use manually verified or approved commercial mileage.",
            "Compare eligible drivers and equipment using their saved pay and cost profiles.",
            "Review the BOOK, NEGOTIATE, DECLINE, or REVIEW REQUIRED recommendation and the thresholds behind it.",
            "Record a counteroffer, decline the opportunity, or book it after the final all-in rate is confirmed.",
            "After booking, upload the RateCon when received; the original evaluation and final booking snapshots remain locked.",
        ),
        "key_points": (
            ("Recommendation", "The result is deterministic decision support based on company settings and entered facts."),
            ("Final rate", "Book only the confirmed all-in amount, then compare it with the RateCon."),
            ("Snapshot", "CarrierOS preserves what was evaluated and what was finally booked for auditability."),
        ),
        "tips": (
            "Enter realistic deadhead, fuel, accessorial, and equipment assumptions before comparing offers.",
            "Use negotiation history instead of overwriting the broker's original offer.",
        ),
        "related": ("ratecon-inbox", "settings", "drivers-equipment"),
    },
    {
        "slug": "ratecon-inbox",
        "group": "daily",
        "icon": "RC",
        "title": "RateCon inbox",
        "route": "/ratecons",
        "summary": "Review a rate confirmation against the booked load before assignment and dispatch.",
        "purpose": (
            "RateCon inbox stores a private uploaded rate confirmation, proposes extracted facts "
            "for human review, compares them with the booking snapshot, and blocks dispatch until "
            "material differences are explicitly resolved."
        ),
        "steps": (
            "Upload the RateCon PDF or supported phone image from a trusted source.",
            "Wait for file validation, malware screening, OCR or text extraction, and candidate matching.",
            "Attach the document to the correct booked load; never rely only on the suggested match.",
            "Verify every extracted field against the original document and review each booking difference.",
            "Approve material differences only after the carrier has actually accepted the changed terms.",
            "Continue to driver and equipment assignment when the RateCon review is complete.",
        ),
        "key_points": (
            ("Human review", "Extraction proposes facts; it does not approve a rate, appointment, fee, or contract term."),
            ("Private storage", "Production uploads require configured encrypted private storage and a clean malware result."),
            ("Dispatch control", "A clean, attached, reviewed RateCon is required before assignment can advance."),
        ),
        "tips": (
            "Check rate, lane, dates, stops, equipment, accessorials, cancellation terms, and special instructions.",
            "Use the audit trail when a booking and RateCon differ instead of silently changing the original quote.",
        ),
        "related": ("rate-quotes", "dispatch", "loads"),
    },
    {
        "slug": "loads",
        "group": "daily",
        "icon": "LD",
        "title": "Loads",
        "route": "/loads",
        "summary": "Maintain the operational and financial record for every shipment.",
        "purpose": (
            "Loads is the system of record for lane, dates, customer, revenue, assigned people "
            "and equipment, status, direct costs, documents, delivery activity, and calculated results."
        ),
        "steps": (
            "Use Add load for a manual shipment or let a booked rate quote create the initial load.",
            "Enter or verify lane, dates, revenue, miles, driver, equipment, direct costs, and whether the load belongs in the model.",
            "Open the load detail to review pay, profit, appointments, RateCon state, delivery history, and documents.",
            "Use Edit to correct permitted fields; preserve the original quote or booking snapshot when one exists.",
            "Update status only as the real shipment progresses and cancel a load when it should no longer move.",
            "Use filters, sorting, or CSV export to review a focused set of load records.",
        ),
        "key_points": (
            ("Include in model", "Turning inclusion off removes the record from modeled totals without deleting its history."),
            ("Calculated results", "Pay and profit are estimates derived from the saved load, driver, unit, and company settings."),
            ("Delivery record", "Driver and office activity remains tied to the same load for later review."),
        ),
        "tips": (
            "Keep pickup and delivery dates accurate because monthly reporting uses the delivery date.",
            "Record accessorial revenue and direct expenses separately so the load result explains itself.",
        ),
        "related": ("dispatch", "money", "ratecon-inbox"),
    },
    {
        "slug": "drivers-equipment",
        "group": "daily",
        "icon": "DE",
        "title": "Drivers and equipment",
        "route": "/drivers",
        "summary": "Create the people, pay rules, trucks, and trailers used by quoting and dispatch.",
        "purpose": (
            "Drivers and equipment holds the operating profiles that feed load assignment, "
            "driver-pay estimates, availability, fixed cost, fuel use, maintenance reserve, and capacity limits."
        ),
        "steps": (
            "Add each active power unit and trailer with a clear internal name and the operating details the model needs.",
            "Create the driver profile with role, contact information, status, and the exact agreed pay model.",
            "Enter only the fields used by that pay model, plus MPG, maintenance reserve, fixed costs, and default equipment where applicable.",
            "Save sourced driver location and availability information when it changes.",
            "Review the profile before quoting or assigning a load, then update it when written terms or equipment change.",
        ),
        "key_points": (
            ("Seven pay models", "Profit split, contractor gross split, owner-operator split, flat per load, loaded mile, total mile, and day rate are supported."),
            ("Unit limits", "The active-power-unit limit comes from the organization's subscription plan."),
            ("Location", "Saved location is user-entered planning data, not live telematics."),
        ),
        "tips": (
            "Use names dispatchers recognize, such as Truck 12 or 40-foot gooseneck, instead of vague labels.",
            "Review written compensation agreements before changing a driver's pay profile.",
        ),
        "related": ("rate-quotes", "dispatch", "money"),
    },
    {
        "slug": "money",
        "group": "daily",
        "icon": "$",
        "title": "Money",
        "route": "/financials",
        "summary": "Analyze load economics, company results, driver balances, and recorded payments.",
        "purpose": (
            "Money combines selected-load reporting, company-wide profit and loss, owner balances, "
            "driver or contractor earnings, and the payments entered in CarrierOS."
        ),
        "steps": (
            "Choose a date range, driver, load, status, or other filter for the selected-load report.",
            "Review revenue, operating expense, estimated load pay, company profit, and results by driver or delivery month.",
            "Open the full-company P&L for overhead, idle fixed cost, true net, reserves, and cash-after-reserve estimates.",
            "Open Record payments and enter each actual payment or draw with the correct payee, amount, date, and reference.",
            "Edit or void an incorrect payment instead of creating an unexplained offset.",
            "Return to driver balances and confirm recorded payments reconcile with the external bank or payroll record.",
        ),
        "key_points": (
            ("Selected vs company-wide", "A driver filter changes selected-load results but does not distort company-wide overhead and idle cost."),
            ("Payment ledger", "CarrierOS tracks records entered by the user; it does not move money or process payroll."),
            ("Professional review", "The reports are operating estimates, not tax, accounting, payroll, or legal advice."),
        ),
        "tips": (
            "Record payments consistently and retain the external transaction reference.",
            "Resolve missing loads, duplicate entries, and model warnings before treating a report as final.",
        ),
        "related": ("loads", "reports", "settings"),
    },
    {
        "slug": "reports",
        "group": "review",
        "icon": "RP",
        "title": "Reports and idle fixed cost",
        "route": "/idle",
        "summary": "Account for fixed equipment cost during non-load periods without distorting load results.",
        "purpose": (
            "The Reports tab opens the idle fixed-cost model. It bridges monthly unit fixed cost "
            "between load-covered days, logged idle periods, unlogged idle time, driver reductions, "
            "and company responsibility."
        ),
        "steps": (
            "Select the month to review and inspect each unit's fixed-cost bridge.",
            "Log an idle or time-off period with the driver, unit, dates, and applicable responsibility treatment.",
            "Use Driver Keeps Truck treatment only when it matches the signed profit-split arrangement.",
            "Review logged and unlogged idle days, any driver-pay reduction, company cost, and model status.",
            "Edit the period or turn off Include in model when the entry is incorrect.",
        ),
        "key_points": (
            ("Unlogged time", "Fixed cost not covered by loads or a valid logged period remains company responsibility."),
            ("Date coverage", "Overlapping, reversed, or incomplete periods create review issues."),
            ("Written terms", "A modeled reduction does not replace the signed compensation agreement or legal review."),
        ),
        "tips": (
            "Review idle bridges monthly before closing management reports.",
            "Use notes to explain unusual downtime, repairs, or planned unavailability.",
        ),
        "related": ("money", "drivers-equipment", "settings"),
    },
    {
        "slug": "shortcuts",
        "group": "review",
        "icon": "SC",
        "title": "Shortcuts",
        "route": "/links",
        "summary": "Keep frequently used load boards, broker portals, and operating tools one click away.",
        "purpose": (
            "Shortcuts is a private bookmark list for the organization. CarrierOS opens the saved "
            "website in a new tab but does not sign in, read the destination, or store its credentials."
        ),
        "steps": (
            "Enter a recognizable link name.",
            "Paste the full http or https website address.",
            "Choose a category such as load board, broker, fuel, routing, finance, or other.",
            "Save the shortcut and test it from the saved-links panel.",
            "Remove links that are obsolete or no longer trusted.",
        ),
        "key_points": (
            ("Private list", "Shortcuts are visible only inside the organization's CarrierOS workspace."),
            ("Bookmark only", "CarrierOS does not connect to, scrape, or authenticate with the linked service."),
            ("Link safety", "Verify the destination domain before entering credentials on any external site."),
        ),
        "tips": (
            "Use the official login page instead of a long session-specific URL.",
            "Keep labels short and specific so dispatch can recognize them quickly.",
        ),
        "related": ("dispatch", "dashboard", "settings"),
    },
    {
        "slug": "compliance",
        "group": "review",
        "icon": "CP",
        "title": "Compliance",
        "route": "/compliance",
        "summary": "Track renewal dates and responsibilities for company, driver, and equipment records.",
        "purpose": (
            "Compliance is a reminder workspace for operating records and expiration dates. "
            "It helps surface due or overdue items but does not verify legal compliance with an agency."
        ),
        "steps": (
            "Add the item name, category, responsible driver or unit, due date, status, and notes.",
            "Review due-soon and overdue items from the Compliance tab and Dashboard alerts.",
            "Update the status and next due date after the real renewal or corrective action is complete.",
            "Remove an entry only when the record is no longer applicable; preserve required evidence elsewhere.",
        ),
        "key_points": (
            ("Reminder system", "CarrierOS relies on user-entered dates and does not query agency or insurer systems."),
            ("Assignment review", "Expired or missing tracked items may affect equipment or driver assignment review."),
            ("Evidence", "Keep official certificates, filings, and source records in the appropriate secure repository."),
        ),
        "tips": (
            "Enter renewal dates early enough to allow processing time.",
            "Assign a specific owner for each item instead of relying on a shared reminder.",
        ),
        "related": ("dispatch", "documents", "onboarding"),
    },
    {
        "slug": "documents",
        "group": "review",
        "icon": "DC",
        "title": "Documents",
        "route": "/documents",
        "summary": "Generate editable operating-document drafts from company-supplied information.",
        "purpose": (
            "Documents creates company-specific drafts such as handbooks, policies, and operating forms. "
            "The generated text is a starting point for qualified legal, safety, payroll, and insurance review."
        ),
        "steps": (
            "Choose the document type and enter the company, effective date, state, contact, and relevant notes.",
            "Generate the draft and read the entire document in the browser.",
            "Download the DOCX when a reviewer needs to edit, redline, or approve it.",
            "Replace placeholder or generic language with the company's actual policy and signed terms.",
            "Issue the document only after the required professional and internal approvals.",
        ),
        "key_points": (
            ("Draft status", "Generated documents are templates, not legal advice or automatically enforceable policies."),
            ("Company facts", "The user is responsible for the accuracy of every supplied name, date, term, and instruction."),
            ("Version control", "Keep the approved version and acknowledgment history outside the draft generator when required."),
        ),
        "tips": (
            "Do not paste Social Security numbers, bank credentials, tax IDs, or identity-document images into notes.",
            "Record the final effective date and approval owner on the issued document.",
        ),
        "related": ("document-audits", "compliance", "onboarding"),
    },
    {
        "slug": "detention-ar",
        "group": "review",
        "icon": "AR",
        "title": "Detention and A/R",
        "route": "/receivables",
        "summary": "Track invoice status, aging, collections attention, and detention claim drafts.",
        "purpose": (
            "Detention and A/R connects delivered work with the amounts expected from customers or brokers. "
            "It tracks user-entered invoices, payment status, aging, and documented detention claims."
        ),
        "steps": (
            "Create the invoice record for the correct load with the expected amount and due date.",
            "Review open and overdue balances by aging bucket.",
            "Mark an invoice paid only after the external payment is verified.",
            "Create a detention claim with arrival, release, free-time, hourly rate, and supporting facts.",
            "Generate the claim draft, verify it against the contract and evidence, then send it outside CarrierOS.",
        ),
        "key_points": (
            ("Tracking only", "CarrierOS does not issue invoices, collect funds, reconcile a bank, or send the detention claim automatically."),
            ("Evidence", "A detention draft is only as strong as the appointment, arrival, release, RateCon, POD, and communication records."),
            ("Aging", "Due and overdue amounts depend on the dates and payment status entered by the user."),
        ),
        "tips": (
            "Use the broker or customer invoice number and retain the external submission confirmation.",
            "Follow the RateCon's notice deadlines and detention terms.",
        ),
        "related": ("loads", "ratecon-inbox", "money"),
    },
    {
        "slug": "weekly-fuel",
        "group": "review",
        "icon": "FL",
        "title": "Weekly fuel",
        "route": "/fuel",
        "summary": "Maintain the diesel-price input used when a load does not have a specific fuel override.",
        "purpose": (
            "Weekly fuel stores dated average diesel prices for operating estimates. CarrierOS uses the "
            "appropriate saved value or configured fallback when calculating modeled fuel cost."
        ),
        "steps": (
            "Enter the effective week or date and the average diesel price used by the company.",
            "Save the record and verify that the current diesel metric reflects the intended value.",
            "Use a load-specific fuel override only when the shipment should not use the weekly or fallback price.",
            "Correct an inaccurate source value before relying on new quote or load estimates.",
        ),
        "key_points": (
            ("Modeled price", "The weekly record is an assumption, not a fuel-card transaction feed."),
            ("Historical math", "A dated price helps explain the estimate used for a past load."),
            ("Fallback", "Settings supplies the fallback value when no applicable weekly record exists."),
        ),
        "tips": (
            "Use one consistent, documented source for the company's weekly average.",
            "Keep fuel-card and receipt records in the accounting system used for actual expense reconciliation.",
        ),
        "related": ("rate-quotes", "loads", "settings"),
    },
    {
        "slug": "growth-mentor",
        "group": "review",
        "icon": "GR",
        "title": "Growth mentor",
        "route": "/growth",
        "summary": "Stress-test an equipment purchase or financing scenario before signing.",
        "purpose": (
            "Growth mentor compares the last 90 days of included-load performance with a proposed equipment "
            "purchase, financing terms, operating assumptions, cash reserve, and company margin targets."
        ),
        "steps": (
            "Review the current 90-day load, revenue, profit, and margin signals.",
            "Enter purchase price, down payment, APR, term, insurance, other fixed cost, and operating assumptions.",
            "Enter expected miles, revenue per mile, MPG, diesel, maintenance, driver pay, and available cash reserve.",
            "Run the audit and review projected payment, cost, contribution, margin, break-even RPM, coverage, and remaining cash.",
            "Validate the scenario with lenders, insurers, mechanics, accountants, attorneys, and realistic freight demand before committing.",
        ),
        "key_points": (
            ("Scenario", "The output is decision support from user inputs, not a forecast, approval, or financing offer."),
            ("Historical window", "Current signals use the prior 90 days of included CarrierOS load records."),
            ("External facts", "Taxes, insurance, downtime, mechanical condition, freight availability, and contract terms require separate review."),
        ),
        "tips": (
            "Run conservative and downside cases instead of relying on one optimistic scenario.",
            "Leave enough cash after the down payment for startup, repair, and collection delays.",
        ),
        "related": ("startup-guide", "money", "settings"),
    },
    {
        "slug": "document-audits",
        "group": "review",
        "icon": "AU",
        "title": "Document audits",
        "route": "/audits",
        "summary": "Extract review findings from supported business documents without silently changing company records.",
        "purpose": (
            "Document audits reviews supported RateCon, business-bank export, and bill documents for structured "
            "findings. The raw audit upload is discarded after processing while limited findings and a checksum remain."
        ),
        "steps": (
            "Choose the supported document type and upload only the business document needed for the review.",
            "Read the scope and privacy notice before submitting.",
            "Open the audit result and compare every extracted figure or finding with the source document.",
            "Investigate discrepancies in the appropriate load, payment, receivable, or external accounting record.",
            "Delete an audit result when it is no longer needed under the company's retention policy.",
        ),
        "key_points": (
            ("No silent changes", "An audit finding never posts a load, payment, journal entry, or accounting correction."),
            ("Limited retention", "CarrierOS retains structured findings, filename, checksum, and metadata rather than the raw audit upload."),
            ("Sensitive data", "Do not upload documents containing SSNs, full account numbers, credentials, tax IDs, or identity images."),
        ),
        "tips": (
            "Redact unnecessary sensitive fields before uploading.",
            "Use a qualified accountant for general-ledger reconciliation and financial-statement conclusions.",
        ),
        "related": ("documents", "money", "ratecon-inbox"),
    },
    {
        "slug": "startup-guide",
        "group": "review",
        "icon": "SU",
        "title": "Startup guide",
        "route": "/startup",
        "summary": "Work through the major authority, safety, insurance, finance, and recordkeeping foundations.",
        "purpose": (
            "Startup guide is a progress checklist for pre-authority and early-stage carriers. It links to "
            "official sources and separates planning progress from actual agency approval."
        ),
        "steps": (
            "Open each checklist item and read the goal, official source, and completion evidence.",
            "Complete the real filing, account setup, policy, training, or business decision outside CarrierOS.",
            "Mark the step complete only after the required evidence exists.",
            "Reopen a step if a filing, policy, or assumption changes.",
            "Use Growth mentor before committing to financed equipment and upgrade the plan when the first active power unit is ready.",
        ),
        "key_points": (
            ("Progress tracker", "A checked box is an internal planning record, not proof of agency, insurer, tax, or legal approval."),
            ("Official sources", "Follow the current instructions on the linked government or program website."),
            ("Professional help", "Use qualified legal, tax, insurance, safety, and accounting professionals where appropriate."),
        ),
        "tips": (
            "Save confirmation numbers and effective dates in the secure system chosen for permanent compliance records.",
            "Build insurance, maintenance, fuel, and collection-delay cash into the launch plan.",
        ),
        "related": ("growth-mentor", "compliance", "billing"),
    },
    {
        "slug": "onboarding",
        "group": "admin",
        "icon": "ON",
        "title": "Onboarding",
        "route": "/onboarding",
        "summary": "Invite an office user into the correct private company workspace with an appropriate role.",
        "purpose": (
            "Onboarding creates a time-limited invitation for a user to join the organization. "
            "The selected role controls what that user can view or manage."
        ),
        "steps": (
            "Enter the person's name and business email.",
            "Choose the least-privilege role that matches the work they must perform.",
            "Create the invitation and send the private onboarding link to that person through a trusted channel.",
            "Ask the invitee to set their own password and confirm access.",
            "Review company users and remove or change access when responsibilities end.",
        ),
        "key_points": (
            ("Private link", "Treat an unused onboarding link as sensitive because it grants entry to the organization."),
            ("Least privilege", "Do not give owner or administrator access for routine read-only or dispatch work."),
            ("Company boundary", "Every invited user belongs to the same isolated organization workspace."),
        ),
        "tips": (
            "Confirm the email address before sharing the invitation.",
            "Do not share one login across multiple people.",
        ),
        "related": ("settings", "billing", "compliance"),
    },
    {
        "slug": "referral-program",
        "group": "admin",
        "icon": "RF",
        "title": "Referral program",
        "route": "/referrals",
        "summary": "Create and administer OTW-authorized driver referral links and commission records.",
        "purpose": (
            "Referral program lets the authorized CarrierOS referral administrator invite an eligible driver, "
            "activate a unique referral link, attribute qualifying subscriptions, track the recurring 50% "
            "commission ledger, and record payouts after the confirmation hold."
        ),
        "steps": (
            "Choose the eligible driver and confirm the email that will receive the private activation link.",
            "Create the invitation, copy the one-time private portal link, and deliver it securely.",
            "The driver reviews and accepts the current Referral Program Terms before the public referral link activates.",
            "Review attributed organizations, qualifying paid invoices, refunds or disputes, the 30-day hold, and available balance.",
            "Complete the real payout outside CarrierOS, then record the payment date and reference in the administrator ledger.",
            "Deactivate or rotate a link when access or eligibility changes.",
        ),
        "key_points": (
            ("Restricted access", "The administration tab appears only to the configured CarrierOS referral administrator."),
            ("Ledger only", "CarrierOS calculates and records commissions but does not move money."),
            ("Required review", "Tax, payroll, advertising-disclosure, contract, and payout requirements need qualified review."),
        ),
        "tips": (
            "Require the driver to disclose the referral relationship when promoting CarrierOS.",
            "Verify cleared customer payment and required tax documentation before paying a commission.",
        ),
        "related": ("drivers-equipment", "billing", "onboarding"),
    },
    {
        "slug": "settings",
        "group": "admin",
        "icon": "ST",
        "title": "Settings",
        "route": "/settings",
        "summary": "Set the company assumptions and decision thresholds used throughout CarrierOS.",
        "purpose": (
            "Settings controls company identity, financial assumptions, overhead, reserves, quote thresholds, "
            "routing fallback values, and other organization-level defaults used by calculations."
        ),
        "steps": (
            "Review company profile and contact information.",
            "Enter the fixed-cost, processing-fee, reserve, owner-distribution, and overhead assumptions that match company policy.",
            "Set quote decision thresholds for margin, deadhead, profit, profit per mile or day, and revenue per mile.",
            "Confirm the fallback diesel price and production routing method.",
            "Save changes, then recheck a representative quote and load to understand the effect.",
            "Use Export company data when an authorized owner needs a portable record of the workspace.",
        ),
        "key_points": (
            ("Organization-wide effect", "Setting changes can change new and recalculated estimates across the workspace."),
            ("Source of truth", "Use documented company policy and verified cost information instead of aspirational targets."),
            ("Data export", "Protect exported company data as confidential business information."),
        ),
        "tips": (
            "Review assumptions at least monthly and whenever insurance, financing, fuel, pay, or overhead changes.",
            "Record why a major threshold changed so later decisions remain explainable.",
        ),
        "related": ("rate-quotes", "money", "billing"),
    },
    {
        "slug": "billing",
        "group": "admin",
        "icon": "BL",
        "title": "Billing",
        "route": "/billing",
        "summary": "Review the plan, trial, active-unit limit, payment portal, upgrades, and cancellation state.",
        "purpose": (
            "Billing shows the organization's CarrierOS subscription status and plan entitlement. "
            "Stripe securely handles payment-method collection, invoices, subscription changes, and the customer portal."
        ),
        "steps": (
            "Review the current plan, subscription status, trial or renewal timing, and active-power-unit limit.",
            "Choose the plan sized for the number of active power units the company needs.",
            "Open secure Stripe Checkout or the Customer Portal to manage the payment method and subscription.",
            "Return to CarrierOS and confirm the webhook-updated status before relying on new entitlements.",
            "Schedule cancellation from Billing when needed and review the effective end of access.",
        ),
        "key_points": (
            ("Stripe hosted", "CarrierOS does not store the complete card number or bank credential."),
            ("Plan limit", "Plans are based on active power units; driver records and office users are not billed per seat."),
            ("Webhook state", "The success redirect does not grant access by itself; verified Stripe events control entitlement."),
        ),
        "tips": (
            "Use the same authorized business email and organization when communicating about a billing issue.",
            "Contact support before creating a second subscription for the same company.",
        ),
        "related": ("settings", "onboarding", "startup-guide"),
    },
)


HELP_GUIDES = {guide["slug"]: guide for guide in _GUIDES}
HELP_GUIDE_LIST = _GUIDES
