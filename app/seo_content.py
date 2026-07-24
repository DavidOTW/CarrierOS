"""Search-focused, people-first content for CarrierOS public solution pages."""

from __future__ import annotations

from typing import Any


SEO_PAGE_ENHANCEMENTS: dict[str, dict[str, Any]] = {
    "small-fleet-trucking-software": {
        "deep_dives": [
            (
                "A shared record for the load and its economics",
                (
                    "A load should not become a different story in dispatch, driver pay, "
                    "receivables, and the month-end review. CarrierOS keeps the lane, "
                    "assigned resources, revenue, miles, direct costs, and estimated result "
                    "connected so the team can work from the same operating record."
                ),
                (
                    "Review active and completed loads from one workspace.",
                    "Keep driver compensation assumptions attached to the work that created the obligation.",
                    "Separate gross revenue from the estimated amount the carrier kept.",
                ),
            ),
            (
                "Structure that can grow with a small carrier",
                (
                    "The workflow is designed for fleets that need repeatability without a "
                    "long enterprise implementation. Plans are based on active power units, "
                    "while driver records and office users remain available for the people "
                    "who operate the business."
                ),
                (
                    "Begin with an owner-operator or small-fleet plan.",
                    "Use mixed driver-pay methods across the same company workspace.",
                    "Keep ELD, payroll, accounting, and regulated compliance systems in their proper roles.",
                ),
            ),
        ],
        "related": (
            "small-fleet-tms",
            "trucking-dispatch-software",
            "driver-settlement-software",
            "trucking-accounts-receivable-software",
        ),
    },
    "driver-settlement-software": {
        "deep_dives": [
            (
                "Seven supported ways to model driver compensation",
                (
                    "CarrierOS supports profit split, contractor gross split, owner-operator "
                    "split, flat per load, loaded-mile rate, total-mile rate, and day rate. "
                    "The method and rate can be configured by driver instead of forcing the "
                    "entire fleet into one formula."
                ),
                (
                    "Preview the effect of the selected pay method on a load.",
                    "Review cumulative earned, paid, and open operating balances.",
                    "Keep payment records connected to the company workspace.",
                ),
            ),
            (
                "A calculation record, not a payroll substitute",
                (
                    "The software helps the carrier calculate and track operating pay "
                    "obligations from the information entered. It does not classify workers, "
                    "withhold or file taxes, transmit payroll, or replace the signed agreement "
                    "and professional payroll, legal, tax, or accounting advice."
                ),
                (
                    "Use written agreements as the source of compensation terms.",
                    "Review estimates before authorizing an external payment.",
                    "Preserve the payment trail for later operating review.",
                ),
            ),
        ],
        "related": (
            "small-fleet-trucking-software",
            "trucking-dispatch-software",
            "load-profitability-calculator",
            "owner-operator-business-software",
        ),
    },
    "load-profitability-calculator": {
        "deep_dives": [
            (
                "Compare the rate with the costs that move the truck",
                (
                    "Loaded miles are only one part of the trip. CarrierOS can include "
                    "deadhead, fuel, maintenance reserve, driver pay, direct load costs, "
                    "fixed-cost days, company fees, and overhead assumptions when estimating "
                    "the carrier result."
                ),
                (
                    "Test an offer before the load is booked.",
                    "Preserve the accepted assumptions when a quote becomes a load.",
                    "Compare the expected result with the completed-load record.",
                ),
            ),
            (
                "Use the estimate as a decision aid",
                (
                    "Every result depends on the quality of the carrier's inputs. The tool "
                    "makes those assumptions visible so an owner or dispatcher can challenge "
                    "fuel price, miles, pay, costs, and margin before relying on the answer."
                ),
                (
                    "Maintain realistic equipment and company cost assumptions.",
                    "Review unexpected accessorials and direct expenses.",
                    "Treat the result as an operational estimate rather than financial advice.",
                ),
            ),
        ],
        "related": (
            "trucking-dispatch-software",
            "small-fleet-tms",
            "driver-settlement-software",
            "hotshot-trucking-software",
        ),
    },
    "carrier-startup-checklist": {
        "deep_dives": [
            (
                "Organize the work before the first dispatch",
                (
                    "The startup workspace separates authority, registration, safety, "
                    "insurance, equipment, cash, and recordkeeping into visible steps. "
                    "Official-source links help the future carrier verify requirements with "
                    "the agencies and professionals responsible for them."
                ),
                (
                    "Track progress without treating a checklist as legal approval.",
                    "Record equipment-finance and operating assumptions before committing cash.",
                    "Prepare the records and decision habits needed for the first load.",
                ),
            ),
            (
                "Move from planning into operations",
                (
                    "The zero-active-unit plan is for preparation. When the first unit is "
                    "ready, the company can move into an operating plan and use the same "
                    "CarrierOS account for quotes, loads, drivers, pay estimates, receivables, "
                    "and profitability."
                ),
                (
                    "Start with a private planning workspace.",
                    "Upgrade when active equipment is ready to operate.",
                    "Continue verifying regulatory, tax, insurance, and legal decisions independently.",
                ),
            ),
        ],
        "related": (
            "owner-operator-business-software",
            "small-fleet-trucking-software",
            "load-profitability-calculator",
            "trucking-compliance-management-software",
        ),
    },
}


ADDITIONAL_SEO_PAGES: dict[str, dict[str, Any]] = {
    "small-fleet-tms": {
        "title": "Small Fleet TMS for 1–20 Trucks | CarrierOS",
        "description": (
            "A practical small fleet TMS for carriers with 1–20 trucks. Connect rate "
            "checks, dispatch, loads, driver pay, receivables, documents, and estimated profit."
        ),
        "card_copy": "Connect the offer-to-cash workflow without enterprise TMS overhead.",
        "eyebrow": "Small fleet TMS",
        "heading": "A transportation management system sized for a small carrier.",
        "lead": (
            "CarrierOS connects pre-book rate decisions, load records, dispatch, driver "
            "compensation, receivables, operating documents, and estimated carrier profit "
            "in one browser-based workspace."
        ),
        "audience": (
            "For U.S. owner-operators and motor carriers with 1–20 power units that have "
            "outgrown disconnected spreadsheets but do not need enterprise implementation."
        ),
        "problem_title": "Small fleets need operating control without software that becomes another operation.",
        "problem_copy": (
            "A traditional TMS can be too narrow, too large, or too expensive for a small "
            "carrier. CarrierOS focuses on the decisions between a broker offer and the cash "
            "the company ultimately keeps, with the load as the shared operating record."
        ),
        "benefits": [
            ("Offer-to-load workflow", "Check the rate, record negotiations, and preserve the accepted assumptions when an offer becomes a load."),
            ("Dispatch records", "Keep stops, dates, contacts, driver, equipment, instructions, and status together."),
            ("Pay and profit", "Estimate the driver obligation and carrier result using the company's configured assumptions."),
            ("Revenue follow-through", "Track paperwork readiness, receivables, detention support, and payment status."),
        ],
        "workflow_title": "Follow the freight from offer to operating result",
        "workflow": [
            ("Evaluate", "Compare the broker offer with miles, costs, driver pay, break-even, and target margin."),
            ("Execute", "Book the load, verify terms, assign resources, and maintain the dispatch record."),
            ("Settle and review", "Track delivery support, driver obligations, receivables, and estimated company profit."),
        ],
        "deep_dives": [
            (
                "What CarrierOS includes",
                (
                    "The workspace brings together the operating records that a small carrier "
                    "uses every day. It is designed to reduce duplicate entry and make the "
                    "financial consequence of a dispatch decision easier to see."
                ),
                (
                    "Rate quotes, negotiation history, loads, assignments, and status.",
                    "Seven driver-pay methods with earned and payment tracking.",
                    "Receivables, detention support, compliance dates, documents, and reports.",
                ),
            ),
            (
                "What remains outside the system",
                (
                    "CarrierOS is not an ELD, GPS tracking service, load board, accounting "
                    "ledger, payroll processor, or regulatory filing service. Those systems "
                    "remain the source of truth for their specialized functions."
                ),
                (
                    "Use ELD and safety systems for hours-of-service and vehicle-compliance records.",
                    "Use banks, payroll providers, and accounting systems for posted financial transactions.",
                    "Verify legal and regulatory obligations with qualified professionals and official agencies.",
                ),
            ),
        ],
        "faqs": [
            ("What does TMS mean in trucking?", "A transportation management system helps organize freight planning and execution. CarrierOS applies that idea to the quote, dispatch, driver-pay, receivables, and profitability workflow of a small motor carrier."),
            ("How large a fleet can use CarrierOS?", "Published plans support owner-operators and fleets with up to 20 active power units. Larger fleets can request a custom plan."),
            ("Does CarrierOS include unlimited office users?", "Published operating plans include unlimited office users and driver records; pricing is based on active power units."),
            ("Is CarrierOS an ELD or accounting platform?", "No. It is an operations and profitability workspace and does not replace an ELD, payroll, tax, legal, insurance, or regulated accounting system."),
        ],
        "related": (
            "small-fleet-trucking-software",
            "trucking-dispatch-software",
            "trucking-accounts-receivable-software",
            "trucking-compliance-management-software",
        ),
    },
    "trucking-dispatch-software": {
        "title": "Trucking Dispatch Software for Small Fleets | CarrierOS",
        "description": (
            "Trucking dispatch software for small carriers. Connect rate decisions, load "
            "details, stops, drivers, equipment, documents, status, pay, and estimated profit."
        ),
        "card_copy": "Keep the load, assignment, instructions, and operating economics connected.",
        "eyebrow": "Trucking dispatch software",
        "heading": "Dispatch the load with the decision and the details still attached.",
        "lead": (
            "CarrierOS helps small carriers move from a reviewed broker offer into a "
            "structured load, driver and equipment assignment, dispatch record, and "
            "completed-load financial review."
        ),
        "audience": (
            "For owner-led fleets, dispatchers, and back-office teams coordinating a small "
            "number of trucks without a separate enterprise implementation team."
        ),
        "problem_title": "A dispatch board should show more than where the truck is going.",
        "problem_copy": (
            "The assignment affects driver pay, equipment availability, deadhead, delivery "
            "paperwork, invoicing, and margin. CarrierOS keeps those operating consequences "
            "close to the load instead of splitting them across messages and spreadsheets."
        ),
        "benefits": [
            ("Structured stops", "Record pickup and delivery addresses, appointment windows, contacts, and driver instructions."),
            ("Driver and equipment assignment", "Connect the load with the selected driver, power unit, and trailer records."),
            ("Readiness checks", "Keep RateCon review, contact, address, appointment, and dispatch details visible before release."),
            ("Connected economics", "Review the assigned driver's pay method and the equipment-specific cost assumptions beside the load."),
        ],
        "workflow_title": "Turn an accepted offer into a controlled dispatch record",
        "workflow": [
            ("Book from the quote", "Preserve the accepted rate, lane, miles, costs, and negotiation context."),
            ("Review and assign", "Confirm the load terms, choose the driver and equipment, and complete the stop details."),
            ("Dispatch and follow through", "Share the authorized load details, track progress, documents, delivery, and the financial result."),
        ],
        "deep_dives": [
            (
                "Designed around dispatch readiness",
                (
                    "CarrierOS makes missing operational details visible before the load is "
                    "released. That gives the office a repeatable place to review the record "
                    "instead of depending on memory or a message thread."
                ),
                (
                    "Review pickup and delivery windows in the facility's local time.",
                    "Keep driver contact and equipment assignments tied to the load.",
                    "Record dispatch approval and driver acknowledgment in the workflow.",
                ),
            ),
            (
                "Clear system boundaries",
                (
                    "The dispatch workspace does not make safety decisions for the carrier, "
                    "guarantee driver availability, or replace ELD hours-of-service records, "
                    "GPS tracking, written rate confirmations, or direct communication."
                ),
                (
                    "Verify safety and hours-of-service feasibility independently.",
                    "Treat navigation links as convenience links, not commercial routing advice.",
                    "Keep the signed RateCon and carrier procedures as controlling records.",
                ),
            ),
        ],
        "faqs": [
            ("Can CarrierOS assign drivers and equipment to loads?", "Yes. The operating workflow connects loads with driver, power-unit, and trailer records and shows assignment or availability conflicts for review."),
            ("Does the dispatch page send the driver load details?", "CarrierOS can create a controlled driver dispatch view with stops, contacts, appointments, instructions, and navigation links after office approval."),
            ("Does CarrierOS track a truck's live GPS location?", "No. Saved locations and availability are user-entered operating records; CarrierOS does not replace a GPS or ELD provider."),
            ("Can dispatch see estimated load profit?", "Yes. The load workflow keeps the configured fuel, cost, driver-pay, and carrier-result assumptions available for operating review."),
        ],
        "related": (
            "small-fleet-tms",
            "rate-confirmation-management-software",
            "load-profitability-calculator",
            "trucking-accounts-receivable-software",
        ),
    },
    "rate-confirmation-management-software": {
        "title": "Rate Confirmation Management for Carriers | CarrierOS",
        "description": (
            "Rate confirmation management for small carriers. Review confirmed load terms "
            "against the booking, document differences, and control dispatch approval."
        ),
        "card_copy": "Compare the RateCon with the booking before the load is released.",
        "eyebrow": "Rate confirmation management",
        "heading": "Catch the booking-to-RateCon difference before it becomes a dispatch problem.",
        "lead": (
            "CarrierOS gives a small carrier a controlled RateCon review workflow that keeps "
            "the original booking assumptions, extracted or entered terms, identified "
            "differences, and human approval together."
        ),
        "audience": (
            "For carrier owners, dispatchers, and operations teams that want a repeatable "
            "review between accepting a broker offer and releasing the load."
        ),
        "problem_title": "The accepted offer and the signed confirmation need an intentional comparison.",
        "problem_copy": (
            "Rates, miles, stops, dates, equipment, accessorials, and instructions can change "
            "between a negotiation and the final document. CarrierOS preserves the booking "
            "snapshot and supports a field-level review before dispatch approval."
        ),
        "benefits": [
            ("Immutable booking context", "Keep the accepted quote assumptions available for comparison after the load is created."),
            ("Document review", "Upload a supported RateCon when secure document storage is configured, or use the controlled manual review path."),
            ("Difference classification", "Separate financial, operational, and informational differences for human review."),
            ("Approval control", "Keep dispatch blocked until required review and safety-sensitive decisions are complete."),
        ],
        "workflow_title": "A reviewable path from document to dispatch",
        "workflow": [
            ("Receive the confirmation", "Associate the RateCon with the intended load and validate the supported file."),
            ("Compare the terms", "Review the confirmed values and their source against the preserved booking snapshot."),
            ("Resolve and approve", "Document material differences, confirm the authorized terms, and continue to dispatch."),
        ],
        "deep_dives": [
            (
                "Human review remains the control",
                (
                    "Where configured providers assist with text or field extraction, their "
                    "output is evidence for review rather than an automatic contract change. "
                    "The carrier remains responsible for reading the document and approving "
                    "the terms."
                ),
                (
                    "Review field source, confidence, and document-page context when available.",
                    "Do not silently overwrite the booked load from extracted text.",
                    "Require explicit approval for material financial or operational differences.",
                ),
            ),
            (
                "Document security depends on production configuration",
                (
                    "CarrierOS uses provider boundaries for private storage and malware "
                    "screening. Production uploads should remain unavailable unless the "
                    "required secure services and operational controls are configured."
                ),
                (
                    "Validate file signature, size, and supported document type.",
                    "Keep private documents out of public pages and search indexes.",
                    "Follow the carrier's retention and access-control procedures.",
                ),
            ),
        ],
        "faqs": [
            ("What RateCon fields can be reviewed?", "The workflow is designed to review important financial and operational terms such as rate, miles, dates, stops, equipment, and instructions, with the exact review depending on the document and configured provider."),
            ("Does CarrierOS automatically change a load from a RateCon?", "No. Extracted or entered values are review evidence. Material changes require an authorized human decision."),
            ("Can a RateCon be uploaded on every deployment?", "Private uploads depend on secure storage and malware-screening configuration. CarrierOS keeps uploads disabled when required production controls are not ready."),
            ("Does RateCon review replace reading the contract?", "No. The carrier must read and verify the governing document and resolve questions with the broker or qualified adviser."),
        ],
        "related": (
            "trucking-dispatch-software",
            "small-fleet-tms",
            "trucking-document-management-software",
            "trucking-accounts-receivable-software",
        ),
    },
    "trucking-document-management-software": {
        "title": "Trucking Document Management for Small Fleets | CarrierOS",
        "description": (
            "Trucking document management for small carriers. Organize operating documents, "
            "delivery support, RateCons, audit findings, retention, and review status."
        ),
        "card_copy": "Keep load documents and review status connected to the operating record.",
        "eyebrow": "Trucking document management",
        "heading": "Put the document beside the decision it supports.",
        "lead": (
            "CarrierOS organizes RateCons, delivery support, company records, audit findings, "
            "and review status inside the carrier's private operating workflow rather than "
            "leaving every document in an unstructured inbox."
        ),
        "audience": (
            "For small motor carriers that need a clearer private record of what was "
            "received, reviewed, accepted, and still missing."
        ),
        "problem_title": "A file name alone does not show whether the operation can rely on the document.",
        "problem_copy": (
            "A carrier needs to know which load or company record a document supports, who "
            "reviewed it, whether a required item is missing, and whether it is ready for the "
            "next step. CarrierOS adds that operating context."
        ),
        "benefits": [
            ("Load-document context", "Associate supported RateCons, BOLs, PODs, receipts, and detention evidence with the relevant load workflow."),
            ("Review status", "Keep upload, screening, extraction, office review, and acceptance states visible where configured."),
            ("Document audits", "Review privacy-limited findings from supported operating and financial documents without silently changing company records."),
            ("Compliance records", "Track selected company-document dates and renewal attention in the private workspace."),
        ],
        "workflow_title": "Receive, review, and use the record intentionally",
        "workflow": [
            ("Associate", "Identify the company record or load that the document supports."),
            ("Validate and review", "Apply configured file, security, extraction, and human-review controls."),
            ("Advance the workflow", "Use accepted evidence for dispatch, delivery, invoicing, detention, or operating follow-up."),
        ],
        "deep_dives": [
            (
                "Privacy-first handling",
                (
                    "Public pages never expose customer documents. Private upload features "
                    "are designed around tenant scoping, access controls, file validation, "
                    "and secure-provider configuration."
                ),
                (
                    "Keep customer and load documents outside public search indexes.",
                    "Do not enable production uploads without the required secure storage controls.",
                    "Limit document access to authorized company workflows.",
                ),
            ),
            (
                "Review support, not automatic accounting",
                (
                    "Document audit findings identify items for a human to review. They do "
                    "not post transactions, reconcile a general ledger, change the load, or "
                    "replace accounting, legal, tax, or compliance review."
                ),
                (
                    "Confirm findings against the original document.",
                    "Resolve discrepancies in the system responsible for the official record.",
                    "Keep an audit trail of the review decision.",
                ),
            ),
        ],
        "faqs": [
            ("Which trucking documents can CarrierOS organize?", "The product includes workflows for supported RateCons, delivery documents such as BOLs and PODs, receipts, detention evidence, selected company records, and privacy-limited document audits."),
            ("Are documents public or searchable?", "No. Customer documents belong in the authenticated private workspace and private routes are blocked from search indexing."),
            ("Does CarrierOS replace cloud file storage?", "CarrierOS adds operating context and controlled workflows; production file storage still depends on a configured secure storage provider."),
            ("Will a document audit change my records automatically?", "No. Findings require human review and do not silently modify loads, accounting values, or official records."),
        ],
        "related": (
            "rate-confirmation-management-software",
            "trucking-accounts-receivable-software",
            "trucking-compliance-management-software",
            "small-fleet-tms",
        ),
    },
    "trucking-accounts-receivable-software": {
        "title": "Trucking Accounts Receivable Tracking | CarrierOS",
        "description": (
            "Trucking accounts receivable tracking for small carriers. Monitor invoice "
            "readiness, aging, payment status, detention support, and load revenue follow-up."
        ),
        "card_copy": "Follow delivered freight through paperwork readiness, aging, and payment.",
        "eyebrow": "Trucking accounts receivable tracking",
        "heading": "A delivered load is not finished until the revenue is followed through.",
        "lead": (
            "CarrierOS helps small carriers track invoice readiness, receivable status, aging, "
            "payments, and detention support beside the load that earned the revenue."
        ),
        "audience": (
            "For owners and back-office teams that need a practical view of outstanding "
            "freight revenue without treating an operations app as the accounting ledger."
        ),
        "problem_title": "Revenue on a load board is not the same as cash received.",
        "problem_copy": (
            "Missing paperwork, unresolved delivery status, detention evidence, invoice dates, "
            "and slow-paying customers can separate completed work from available cash. "
            "CarrierOS keeps those follow-up items visible."
        ),
        "benefits": [
            ("Invoice readiness", "See whether delivery and required paperwork are ready for the carrier's invoicing process."),
            ("Aging view", "Track invoice date, due date, open balance, and aging status from the information entered."),
            ("Payment records", "Record customer payments against load receivables for operating follow-up."),
            ("Detention support", "Keep qualifying event times, notes, and supporting documents connected to the claim workflow."),
        ],
        "workflow_title": "Carry the load record through revenue collection",
        "workflow": [
            ("Complete the delivery record", "Confirm load status and collect the required delivery support."),
            ("Track the receivable", "Record invoice timing, amount, due date, and open balance."),
            ("Follow exceptions", "Review aging, missing support, detention, disputes, and recorded payment status."),
        ],
        "deep_dives": [
            (
                "An operations view of accounts receivable",
                (
                    "CarrierOS connects the open balance with the load, customer, delivery "
                    "support, and detention context that created it. That helps an owner decide "
                    "what to follow up without reconstructing the history from several tools."
                ),
                (
                    "Prioritize overdue and exception-bearing receivables.",
                    "Keep delivery and detention evidence close to the operating record.",
                    "Review open freight revenue alongside load profitability and cash needs.",
                ),
            ),
            (
                "Your accounting system remains the financial source of truth",
                (
                    "CarrierOS does not post bank transactions, perform general-ledger "
                    "reconciliation, submit invoices to every customer, or replace accounting "
                    "and factoring records. Entered payment status should be verified against "
                    "the responsible financial system."
                ),
                (
                    "Reconcile recorded payments with bank, factor, and accounting statements.",
                    "Follow customer and broker invoicing requirements independently.",
                    "Use qualified accounting and legal help for disputes and financial reporting.",
                ),
            ),
        ],
        "faqs": [
            ("Can CarrierOS show overdue freight invoices?", "Yes. Using the invoice and due-date information entered, the receivables view can organize open balances and aging for operating follow-up."),
            ("Does CarrierOS send invoices or collect payments?", "CarrierOS tracks the operating receivable and payment records; it does not guarantee invoice delivery, collect customer funds, or replace a bank, factor, or accounting platform."),
            ("Can detention be tracked with the load?", "Yes. The workflow can keep qualifying times, notes, status, amount, and supporting evidence connected to the load for review."),
            ("Is the receivables report a general ledger?", "No. It is an operations record and should be reconciled with the carrier's accounting and banking systems."),
        ],
        "related": (
            "trucking-document-management-software",
            "small-fleet-tms",
            "load-profitability-calculator",
            "trucking-dispatch-software",
        ),
    },
    "trucking-compliance-management-software": {
        "title": "Trucking Compliance Tracking for Small Fleets | CarrierOS",
        "description": (
            "Trucking compliance tracking for small fleets. Organize selected driver, "
            "equipment, insurance, registration, and company renewal dates with visible alerts."
        ),
        "card_copy": "Organize selected renewal dates and records without confusing tracking with verification.",
        "eyebrow": "Trucking compliance tracking",
        "heading": "Keep important renewal dates visible before they become operating surprises.",
        "lead": (
            "CarrierOS gives a small carrier a private place to track selected driver, "
            "equipment, insurance, registration, company, and document dates alongside the "
            "people and assets they affect."
        ),
        "audience": (
            "For owner-led motor carriers that want an operating reminder layer around the "
            "records they still verify with official systems and qualified professionals."
        ),
        "problem_title": "A calendar reminder without the operating context is easy to miss.",
        "problem_copy": (
            "Renewals and expirations affect whether a driver, unit, trailer, or company "
            "record is ready for work. CarrierOS brings selected dates into the same "
            "workspace used to review the fleet."
        ),
        "benefits": [
            ("Date tracking", "Record selected expiration and renewal dates for drivers, equipment, insurance, registration, and company records."),
            ("Visible attention", "Surface upcoming or past-due items in the operating workspace for human review."),
            ("Asset context", "Keep the date beside the driver, unit, trailer, or company record it affects."),
            ("Startup continuity", "Carry selected planning and readiness records into the operating workflow as the carrier grows."),
        ],
        "workflow_title": "Record, review, verify, and renew",
        "workflow": [
            ("Enter the responsible record", "Record the date and relevant driver, asset, policy, registration, or company item."),
            ("Review attention windows", "Use the compliance view and dashboard exceptions to identify upcoming or overdue items."),
            ("Verify outside CarrierOS", "Complete the official renewal or correction, then update the private operating record."),
        ],
        "deep_dives": [
            (
                "Tracking is not regulatory verification",
                (
                    "CarrierOS displays the information the company enters. It does not query "
                    "every agency, certify compliance, determine driver qualification, monitor "
                    "hours of service, or make a vehicle safe to operate."
                ),
                (
                    "Verify authority, registration, insurance, and driver status in official systems.",
                    "Use ELD, maintenance, drug-and-alcohol, and safety programs for their regulated functions.",
                    "Do not dispatch based only on a CarrierOS reminder.",
                ),
            ),
            (
                "A practical review habit for a small fleet",
                (
                    "A regular review turns the tracker into a useful control. Assign someone "
                    "to confirm upcoming items, preserve supporting records, and update the "
                    "workspace after the authoritative source is verified."
                ),
                (
                    "Review near-term expirations on a consistent schedule.",
                    "Escalate missing or conflicting information before assignment.",
                    "Keep internal records current after official action is complete.",
                ),
            ),
        ],
        "faqs": [
            ("Does CarrierOS verify FMCSA compliance?", "No. CarrierOS tracks selected user-entered records and dates. The carrier must verify status with FMCSA, state agencies, insurers, ELD and safety providers, and qualified professionals."),
            ("Can compliance dates affect an assignment review?", "CarrierOS can surface recorded expiration concerns for human review, but the carrier remains responsible for the legal and safety decision."),
            ("Does CarrierOS replace a DQ file or ELD?", "No. It does not replace required driver qualification files, ELD records, maintenance programs, clearinghouse processes, or official systems."),
            ("Can startup checklist items be tracked before the first truck?", "Yes. The Carrier Startup plan organizes readiness questions and official-source links before active operations begin."),
        ],
        "related": (
            "carrier-startup-checklist",
            "trucking-document-management-software",
            "trucking-dispatch-software",
            "small-fleet-tms",
        ),
    },
    "owner-operator-business-software": {
        "title": "Owner-Operator Business Software | CarrierOS",
        "description": (
            "Owner-operator business software for rate checks, loads, expenses, documents, "
            "receivables, and estimated profit. Start with up to two active power units."
        ),
        "card_copy": "See the business behind the truck, from broker offer to estimated profit.",
        "eyebrow": "Owner-operator business software",
        "heading": "Run the business behind the truck with the load economics in view.",
        "lead": (
            "CarrierOS helps an owner-operator evaluate freight, manage active loads, track "
            "operating costs and receivables, and understand the estimated amount the "
            "business kept after the assumptions entered."
        ),
        "audience": (
            "For independent owner-operators, two-truck operations, and drivers preparing "
            "to become carrier owners."
        ),
        "problem_title": "Gross revenue can look healthy while the business underneath it is strained.",
        "problem_copy": (
            "Deadhead, fuel, maintenance, fixed costs, fees, driver obligations, and slow "
            "receivables all affect what a load contributes. CarrierOS keeps those questions "
            "in the operating workflow."
        ),
        "benefits": [
            ("Pre-book rate check", "Compare an offer with miles, costs, break-even, target, and estimated margin."),
            ("Load and document control", "Keep the lane, stops, contacts, status, RateCon review, and delivery support together."),
            ("Owner-operator economics", "Model the configured owner-operator or company cost structure without treating gross as profit."),
            ("Cash follow-through", "Track operating expenses, receivables, payments, and selected recurring obligations."),
        ],
        "workflow_title": "Use the same numbers before, during, and after the load",
        "workflow": [
            ("Decide", "Enter the offer and realistic trip and business-cost assumptions."),
            ("Operate", "Book, dispatch, document, and complete the load from one private workspace."),
            ("Review", "Compare revenue, costs, open receivables, and estimated owner result."),
        ],
        "deep_dives": [
            (
                "For the first truck and the next one",
                (
                    "The Owner-Operator plan supports up to two active power units. It gives "
                    "a solo carrier room for a second unit while keeping the same operating "
                    "records, driver-pay options, and review workflow."
                ),
                (
                    "Plans are based on active power units rather than office seats.",
                    "Use the compensation model appropriate to each configured driver relationship.",
                    "Upgrade the fleet plan as active equipment grows.",
                ),
            ),
            (
                "Know what the software does not decide",
                (
                    "CarrierOS cannot tell an owner whether to buy a truck, accept a load, "
                    "classify a worker, or take a tax position. It organizes assumptions and "
                    "shows operating estimates so the owner can make a better-informed review."
                ),
                (
                    "Verify miles, rates, contracts, and costs before relying on the estimate.",
                    "Use professional tax, accounting, insurance, and legal guidance.",
                    "Keep safety and regulatory decisions in the responsible systems and procedures.",
                ),
            ),
        ],
        "faqs": [
            ("How many trucks are included in the Owner-Operator plan?", "The published Owner-Operator plan supports up to two active power units and includes unlimited driver records and office users."),
            ("Can a leased-on or contractor pay arrangement be modeled?", "CarrierOS supports seven driver-pay methods, including contractor gross split and owner-operator split, using the terms the company configures."),
            ("Can I try CarrierOS before creating an account?", "Yes. The public live demo uses fictional sample data and does not save changes."),
            ("Does CarrierOS provide tax or legal advice?", "No. It provides operating records and estimates and does not replace tax, accounting, legal, insurance, payroll, or regulatory professionals."),
        ],
        "related": (
            "load-profitability-calculator",
            "carrier-startup-checklist",
            "hotshot-trucking-software",
            "small-fleet-trucking-software",
        ),
    },
    "box-truck-fleet-management-software": {
        "title": "Box Truck Fleet Management Software | CarrierOS",
        "description": (
            "Box truck fleet management software for owner-operators and small carriers. "
            "Track quotes, dispatch, drivers, costs, pay, receivables, and estimated load profit."
        ),
        "card_copy": "Manage box-truck freight with cost, pay, and receivable context.",
        "eyebrow": "Box truck fleet management",
        "heading": "Manage box-truck freight as a business, not only a calendar of stops.",
        "lead": (
            "CarrierOS helps box-truck owner-operators and small fleets connect broker offers, "
            "loaded and empty miles, dispatch details, driver pay, operating costs, delivery "
            "support, and receivables."
        ),
        "audience": (
            "For independent carriers and small fleets operating straight trucks or 26-foot "
            "box trucks in local, regional, expedited, or dedicated freight."
        ),
        "problem_title": "Shorter equipment does not make the operating math simpler.",
        "problem_copy": (
            "Box-truck work can include meaningful deadhead, multiple appointments, driver "
            "pay, fuel, maintenance, tolls, accessorials, and waiting time. CarrierOS keeps "
            "those inputs beside the rate and load record."
        ),
        "benefits": [
            ("Equipment-aware records", "Maintain unit details and use the operating assumptions entered for the assigned equipment."),
            ("Multi-stop dispatch context", "Record pickup and delivery stops, local appointment times, contacts, and instructions."),
            ("Flexible driver pay", "Use the configured gross split, profit split, mileage, flat-load, day-rate, or owner-operator method."),
            ("Revenue follow-through", "Keep POD support, detention, receivables, and payment status tied to completed work."),
        ],
        "workflow_title": "Evaluate and follow every box-truck load",
        "workflow": [
            ("Price the movement", "Enter the rate, loaded miles, empty miles, expected dates, and realistic cost assumptions."),
            ("Dispatch the details", "Assign the driver and unit, verify stops and terms, and preserve the load record."),
            ("Close the loop", "Collect delivery support, track the receivable, and review the estimated result."),
        ],
        "deep_dives": [
            (
                "Useful across local, regional, and dedicated work",
                (
                    "CarrierOS does not force every load into a long-haul tractor-trailer "
                    "model. The carrier enters the miles, trip dates, stops, equipment, pay "
                    "method, costs, and accessorials that fit the actual work."
                ),
                (
                    "Compare recurring or dedicated lanes with the same cost framework.",
                    "Capture direct costs and waiting-time support that affect the result.",
                    "Review performance by load, driver, and operating period.",
                ),
            ),
            (
                "Not a load board or vehicle telematics service",
                (
                    "CarrierOS organizes opportunities and loads the carrier enters. It does "
                    "not source freight, guarantee rates, dispatch automatically, or provide "
                    "live vehicle location and routing."
                ),
                (
                    "Use broker, shipper, and load-board relationships to source opportunities.",
                    "Verify equipment suitability and operating authority for each load.",
                    "Use commercial routing and safety systems for route and vehicle decisions.",
                ),
            ),
        ],
        "faqs": [
            ("Can CarrierOS be used for a 26-foot box truck?", "Yes. CarrierOS can organize straight-truck and box-truck operating records using the equipment, mileage, cost, pay, and load details the carrier enters."),
            ("Can I track multiple stops and appointments?", "Yes. The dispatch workflow supports structured pickup and delivery stops, appointment windows, contacts, and instructions."),
            ("Does CarrierOS find box-truck loads?", "No. It is not a load board or brokerage. It helps the carrier evaluate and manage opportunities and loads sourced elsewhere."),
            ("Can company drivers and contractors use different pay methods?", "Yes. Seven supported compensation methods can be configured by driver, subject to the company's agreements and independent legal review."),
        ],
        "related": (
            "trucking-dispatch-software",
            "load-profitability-calculator",
            "driver-settlement-software",
            "owner-operator-business-software",
        ),
    },
    "hotshot-trucking-software": {
        "title": "Hotshot Trucking Software for Small Carriers | CarrierOS",
        "description": (
            "Hotshot trucking software for rate checks, dispatch, truck and trailer records, "
            "driver pay, expenses, documents, receivables, and estimated load profit."
        ),
        "card_copy": "Connect hotshot rates, deadhead, equipment, pay, costs, and load results.",
        "eyebrow": "Hotshot trucking software",
        "heading": "Make the hotshot rate answer to the truck, trailer, miles, and costs.",
        "lead": (
            "CarrierOS helps hotshot owner-operators and small fleets evaluate offers, assign "
            "truck and trailer records, manage dispatch details, model driver pay, and review "
            "the estimated result after operating costs."
        ),
        "audience": (
            "For carriers operating pickup trucks and flatbed or gooseneck trailers in "
            "regional, expedited, dedicated, or general hotshot freight."
        ),
        "problem_title": "A strong rate per mile can still hide deadhead and equipment cost.",
        "problem_copy": (
            "Hotshot profitability changes with empty miles, fuel economy, trailer and truck "
            "costs, maintenance, securement needs, driver compensation, and the days committed. "
            "CarrierOS makes the carrier's assumptions visible."
        ),
        "benefits": [
            ("Truck and trailer records", "Keep power-unit and trailer details available for assignment and operating review."),
            ("Deadhead-aware rate checks", "Include loaded and empty miles when comparing the offered rate with estimated cost and margin."),
            ("Mixed pay arrangements", "Model mileage, flat-load, day-rate, gross-split, profit-split, or owner-operator compensation by driver."),
            ("Load-level review", "Connect the dispatch record, documents, direct expenses, receivable, and estimated carrier result."),
        ],
        "workflow_title": "Evaluate the full hotshot movement",
        "workflow": [
            ("Enter the offer", "Record the lane, rate, loaded and empty miles, dates, and direct load costs."),
            ("Apply the operating setup", "Choose the driver, truck, trailer, pay method, and company cost assumptions."),
            ("Review and follow through", "Compare break-even and margin, run the load, collect support, and track payment."),
        ],
        "deep_dives": [
            (
                "Equipment combinations stay visible",
                (
                    "A hotshot operation may use different trucks and trailers with different "
                    "availability, compatibility, and cost assumptions. CarrierOS keeps the "
                    "selected records connected to the assignment for human review."
                ),
                (
                    "Record power units and trailers separately.",
                    "Review conflicts and selected compatibility information before dispatch.",
                    "Maintain realistic fuel, maintenance, fixed-cost, and pay assumptions.",
                ),
            ),
            (
                "The carrier still owns the safety and legal decision",
                (
                    "Software cannot determine whether a combination, cargo, route, securement "
                    "method, driver, or authority is legal and safe. The company must verify "
                    "weight, dimensions, CDL requirements, permits, insurance, hours of "
                    "service, and cargo securement independently."
                ),
                (
                    "Use authoritative vehicle, licensing, permit, and safety information.",
                    "Do not treat an equipment suggestion as dispatch authorization.",
                    "Confirm the written load terms and cargo requirements before accepting.",
                ),
            ),
        ],
        "faqs": [
            ("Can CarrierOS track a hotshot truck and trailer separately?", "Yes. The workspace includes separate power-unit and trailer records that can be connected to load assignments."),
            ("Does the profitability estimate include deadhead?", "Yes. Loaded and empty miles can be entered so fuel, maintenance, pay, and margin assumptions reflect the fuller movement."),
            ("Does CarrierOS determine CDL or permit requirements?", "No. The carrier must verify licensing, weight, dimension, permit, insurance, safety, and regulatory requirements with authoritative sources."),
            ("Can a hotshot fleet use mixed driver-pay methods?", "Yes. CarrierOS supports seven methods by driver, including loaded-mile, total-mile, flat-load, day-rate, gross-split, profit-split, and owner-operator structures."),
        ],
        "related": (
            "load-profitability-calculator",
            "trucking-dispatch-software",
            "driver-settlement-software",
            "owner-operator-business-software",
        ),
    },
}


SOLUTION_GROUPS = (
    {
        "eyebrow": "Core operations",
        "title": "Plan, dispatch, document, and review the freight.",
        "copy": "Keep the operating record connected from the first rate check through delivery.",
        "slugs": (
            "small-fleet-tms",
            "trucking-dispatch-software",
            "rate-confirmation-management-software",
            "trucking-document-management-software",
        ),
    },
    {
        "eyebrow": "Money and control",
        "title": "See what is owed, open, and estimated to remain.",
        "copy": "Connect driver obligations, load economics, receivables, and selected compliance attention.",
        "slugs": (
            "driver-settlement-software",
            "load-profitability-calculator",
            "trucking-accounts-receivable-software",
            "trucking-compliance-management-software",
        ),
    },
    {
        "eyebrow": "Business stage and equipment",
        "title": "Use a workflow that fits the carrier you are building.",
        "copy": "Start before the first truck or manage the box-truck, hotshot, and mixed small-fleet operation already moving.",
        "slugs": (
            "carrier-startup-checklist",
            "owner-operator-business-software",
            "box-truck-fleet-management-software",
            "hotshot-trucking-software",
        ),
    },
)
