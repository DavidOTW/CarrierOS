from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader


MAX_AUDIT_FILE_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 40
MAX_EXTRACTED_CHARACTERS = 200_000
ALLOWED_AUDIT_EXTENSIONS = {".pdf", ".csv"}


class AuditFileError(ValueError):
    """Raised when an uploaded audit file cannot be safely processed."""


def _safe_filename(value: str) -> str:
    name = Path(str(value or "document")).name.strip().replace("\x00", "")
    name = "".join(character for character in name if character.isprintable())
    return (name or "document")[:255]


def _amount(value: Any) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = re.sub(r"[^0-9.\-]", "", raw)
    if cleaned in {"", "-", "."}:
        return None
    try:
        result = float(cleaned)
    except ValueError:
        return None
    return -abs(result) if negative else result


def _normalized_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().casefold()).strip()


def _find_column(headers: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {_normalized_header(header): header for header in headers}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    for normalized_name, original in normalized.items():
        if any(candidate in normalized_name for candidate in candidates):
            return original
    return None


def _parse_date(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, pattern)
        except ValueError:
            continue
    return None


def _csv_summary(payload: bytes) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = payload.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise AuditFileError("The CSV encoding could not be read.") from exc
    if "\x00" in text:
        raise AuditFileError("The uploaded CSV contains unsupported binary data.")
    reader = csv.DictReader(io.StringIO(text))
    headers = [header for header in (reader.fieldnames or []) if header]
    if not headers:
        raise AuditFileError("The CSV does not contain a header row.")
    amount_column = _find_column(headers, ("amount", "transaction amount"))
    debit_column = _find_column(headers, ("debit", "withdrawal", "withdrawals", "charge"))
    credit_column = _find_column(headers, ("credit", "deposit", "deposits"))
    date_column = _find_column(headers, ("date", "transaction date", "posted date", "posting date"))
    type_column = _find_column(headers, ("type", "transaction type", "credit debit"))
    if not amount_column and not debit_column and not credit_column:
        raise AuditFileError(
            "The CSV needs an Amount column or separate Debit and Credit columns."
        )

    deposits = 0.0
    withdrawals = 0.0
    transaction_count = 0
    dates: list[datetime] = []
    for row in reader:
        transaction_count += 1
        if date_column:
            parsed_date = _parse_date(row.get(date_column))
            if parsed_date:
                dates.append(parsed_date)
        if debit_column or credit_column:
            debit = _amount(row.get(debit_column)) if debit_column else None
            credit = _amount(row.get(credit_column)) if credit_column else None
            withdrawals += abs(debit or 0.0)
            deposits += abs(credit or 0.0)
            continue
        value = _amount(row.get(amount_column))
        if value is None:
            continue
        transaction_type = str(row.get(type_column) or "").casefold() if type_column else ""
        if "debit" in transaction_type or "withdraw" in transaction_type or value < 0:
            withdrawals += abs(value)
        else:
            deposits += value
    return {
        "deposits": round(deposits, 2),
        "withdrawals": round(withdrawals, 2),
        "transaction_count": transaction_count,
        "first_transaction_date": min(dates).date().isoformat() if dates else None,
        "last_transaction_date": max(dates).date().isoformat() if dates else None,
        "extraction_method": "csv_transactions",
    }


def _pdf_text(payload: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(payload), strict=True)
    except Exception as exc:
        raise AuditFileError("The PDF could not be opened. Export a new PDF and try again.") from exc
    if reader.is_encrypted:
        raise AuditFileError("Password-protected PDFs are not supported. Export an unlocked copy.")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise AuditFileError(f"PDFs are limited to {MAX_PDF_PAGES} pages per audit.")
    parts: list[str] = []
    try:
        for page in reader.pages:
            parts.append(page.extract_text() or "")
            if sum(len(part) for part in parts) > MAX_EXTRACTED_CHARACTERS:
                raise AuditFileError("The PDF contains too much extractable text for one audit.")
    except AuditFileError:
        raise
    except Exception as exc:
        raise AuditFileError("CarrierOS could not safely extract text from this PDF.") from exc
    text = "\n".join(parts).strip()
    if len(text) < 40:
        raise AuditFileError(
            "No machine-readable text was found. Scanned-image PDFs need OCR before upload, or use CSV."
        )
    return text


def _labeled_amount(text: str, labels: tuple[str, ...]) -> float | None:
    for label in labels:
        pattern = rf"{label}\s*(?:[:\-]|is)?\s*\$?\s*([\d,]+(?:\.\d{{2}})?)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _amount(match.group(1))
    return None


def _pdf_bank_summary(text: str) -> dict[str, Any]:
    return {
        "deposits": _labeled_amount(
            text,
            (r"total deposits(?: and additions)?", r"deposits and other additions", r"total credits"),
        ),
        "withdrawals": _labeled_amount(
            text,
            (r"total withdrawals(?: and subtractions)?", r"withdrawals and other subtractions", r"total debits"),
        ),
        "ending_balance": _labeled_amount(text, (r"ending balance", r"closing balance", r"new balance")),
        "extraction_method": "pdf_labeled_totals",
    }


def _ratecon_summary(text: str) -> dict[str, Any]:
    reference_match = re.search(
        r"(?:load|confirmation|rate confirmation)\s*(?:number|no\.?|#)?\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-]{2,})",
        text,
        re.IGNORECASE,
    )
    rate = _labeled_amount(
        text,
        (r"total (?:agreed )?rate", r"all[- ]in rate", r"total carrier pay", r"linehaul rate"),
    )
    return {
        "reference": reference_match.group(1) if reference_match else None,
        "rate": rate,
        "extraction_method": "pdf_ratecon_labels",
    }


def _bill_summary(text: str) -> dict[str, Any]:
    due_date_match = re.search(
        r"(?:payment )?due date\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})",
        text,
        re.IGNORECASE,
    )
    return {
        "amount_due": _labeled_amount(
            text,
            (r"total amount due", r"amount due", r"balance due", r"new balance"),
        ),
        "due_date": due_date_match.group(1) if due_date_match else None,
        "extraction_method": "pdf_bill_labels",
    }


def _variance(observed: float, expected: float) -> tuple[float, float | None]:
    amount = observed - expected
    return round(amount, 2), (amount / expected if expected else None)


def _money(value: float | None) -> str:
    return "Not extracted" if value is None else f"${value:,.2f}"


def audit_uploaded_document(
    *,
    document_type: str,
    filename: str,
    content_type: str,
    payload: bytes,
    context: dict[str, Any],
) -> dict[str, Any]:
    safe_name = _safe_filename(filename)
    extension = Path(safe_name).suffix.casefold()
    if extension not in ALLOWED_AUDIT_EXTENSIONS:
        raise AuditFileError("Only text-based PDF and CSV files are accepted.")
    if not payload:
        raise AuditFileError("The uploaded file is empty.")
    if len(payload) > MAX_AUDIT_FILE_BYTES:
        raise AuditFileError("Files are limited to 8 MB per audit.")
    if extension == ".pdf" and not payload.startswith(b"%PDF-"):
        raise AuditFileError("The file extension says PDF, but the file is not a PDF.")
    if extension == ".csv" and payload.startswith(b"%PDF-"):
        raise AuditFileError("The file extension does not match the uploaded file.")
    if document_type not in {"ratecon", "bank_statement", "bill_statement"}:
        raise AuditFileError("Choose a supported document type.")
    if document_type in {"ratecon", "bill_statement"} and extension != ".pdf":
        raise AuditFileError("Rate confirmations and bill statements currently require a text-based PDF.")

    text = _pdf_text(payload) if extension == ".pdf" else ""
    if document_type == "bank_statement":
        extracted = _csv_summary(payload) if extension == ".csv" else _pdf_bank_summary(text)
        result = _audit_bank(extracted, context)
    elif document_type == "ratecon":
        extracted = _ratecon_summary(text)
        result = _audit_ratecon(extracted, context)
    else:
        extracted = _bill_summary(text)
        result = _audit_bill(extracted, context)
    result.update(
        filename=safe_name,
        content_type=(content_type or "application/octet-stream")[:100],
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        raw_file_retained=False,
    )
    return result


def _audit_bank(extracted: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    deposits = extracted.get("deposits")
    withdrawals = extracted.get("withdrawals")
    expected_revenue = float(context.get("expected_revenue") or 0)
    expected_expense = float(context.get("expected_expense") or 0)
    findings: list[dict[str, str]] = []
    metrics = [
        {"label": "Statement deposits", "observed": deposits, "expected": expected_revenue},
        {"label": "Statement withdrawals", "observed": withdrawals, "expected": expected_expense},
    ]
    for observed, expected, subject in (
        (deposits, expected_revenue, "revenue"),
        (withdrawals, expected_expense, "operating expense"),
    ):
        if observed is None:
            findings.append({
                "severity": "warn",
                "title": f"{subject.title()} total needs review",
                "detail": f"CarrierOS could not reliably extract the statement {subject} total.",
                "action": "Enter or export a bank CSV with Date and Amount (or Debit/Credit) columns.",
            })
            continue
        difference, pct = _variance(float(observed), expected)
        if expected <= 0:
            findings.append({
                "severity": "warn",
                "title": f"No CarrierOS {subject} estimate for this period",
                "detail": f"The statement shows {_money(float(observed))}, but the selected period has no matching model estimate.",
                "action": "Check the statement period and enter any missing loads or operating costs.",
            })
        elif pct is not None and abs(pct) <= 0.10:
            findings.append({
                "severity": "good",
                "title": f"{subject.title()} is within 10%",
                "detail": f"Statement activity differs from the CarrierOS estimate by {_money(difference)}.",
                "action": "Review timing items, transfers, and outstanding receivables before marking the period reconciled.",
            })
        else:
            findings.append({
                "severity": "bad" if pct is not None and abs(pct) > 0.20 else "warn",
                "title": f"{subject.title()} variance needs attention",
                "detail": f"Statement activity differs from the CarrierOS estimate by {_money(difference)} ({abs(pct or 0):.1%}).",
                "action": "Check unentered loads, factoring timing, transfers, owner draws, loan payments, and recurring expenses before adjusting an estimate.",
            })
    findings.append({
        "severity": "info",
        "title": "Cash activity is not accrual accounting",
        "detail": "Bank deposits and withdrawals can occur in a different period than the load revenue or expense they relate to.",
        "action": "Use this as a discrepancy screen, then reconcile with a bookkeeper or accounting system.",
    })
    return {
        "status": "review_required" if any(item["severity"] in {"warn", "bad"} for item in findings) else "matched",
        "summary": f"Compared bank activity with CarrierOS estimates for {context.get('period_label') or 'the selected period'}.",
        "extracted": extracted,
        "metrics": metrics,
        "findings": findings,
    }


def _audit_ratecon(extracted: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    expected = float(context.get("expected_revenue") or 0)
    observed = extracted.get("rate")
    findings: list[dict[str, str]] = []
    if observed is None:
        findings.append({
            "severity": "warn", "title": "Rate needs manual confirmation",
            "detail": "CarrierOS did not find a clearly labeled all-in or total carrier rate.",
            "action": "Open the source RateCon and verify the revenue, accessorials, and deductions before dispatch.",
        })
    else:
        difference, pct = _variance(float(observed), expected)
        findings.append({
            "severity": "good" if abs(difference) < 0.01 else "bad",
            "title": "Rate matches the load" if abs(difference) < 0.01 else "Rate differs from the load",
            "detail": f"RateCon {_money(float(observed))}; CarrierOS load {_money(expected)}; variance {_money(difference)}.",
            "action": "No rate adjustment suggested." if abs(difference) < 0.01 else "Verify accessorials and update the load revenue only after confirming the signed RateCon.",
        })
    missing = context.get("dispatch_blockers") or []
    if missing:
        findings.append({
            "severity": "warn", "title": "Driver dispatch is not ready",
            "detail": " ".join(str(item) for item in missing),
            "action": "Complete the verified pickup, delivery, appointment, and driver-phone fields on the load.",
        })
    findings.append({
        "severity": "info", "title": "Raw RateCon discarded after audit",
        "detail": "CarrierOS saved the checksum and findings, not the uploaded contract file.",
        "action": "Retain the signed RateCon in your approved document-management or accounting system.",
    })
    return {
        "status": "review_required" if any(item["severity"] in {"warn", "bad"} for item in findings) else "matched",
        "summary": f"Compared the uploaded RateCon with load {context.get('load_number') or ''}.",
        "extracted": extracted,
        "metrics": [{"label": "RateCon total", "observed": observed, "expected": expected}],
        "findings": findings,
    }


def _audit_bill(extracted: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    observed = extracted.get("amount_due")
    expected = float(context.get("expected_amount") or 0)
    findings: list[dict[str, str]] = []
    if observed is None:
        findings.append({
            "severity": "warn", "title": "Bill total needs manual confirmation",
            "detail": "CarrierOS did not find a clearly labeled amount due.",
            "action": "Review the bill and enter the recurring monthly estimate manually before making changes.",
        })
    elif expected <= 0:
        findings.append({
            "severity": "warn", "title": "No matching monthly estimate",
            "detail": f"The bill shows {_money(float(observed))}, but the linked estimate is zero or not selected.",
            "action": "Add or select the matching overhead item in Settings after confirming this is a recurring business cost.",
        })
    else:
        difference, pct = _variance(float(observed), expected)
        findings.append({
            "severity": "good" if abs(pct or 0) <= 0.10 else ("bad" if abs(pct or 0) > 0.20 else "warn"),
            "title": "Bill is within 10% of estimate" if abs(pct or 0) <= 0.10 else "Bill differs from the estimate",
            "detail": f"Bill {_money(float(observed))}; monthly estimate {_money(expected)}; variance {_money(difference)} ({abs(pct or 0):.1%}).",
            "action": "Keep the current estimate and monitor the next bill." if abs(pct or 0) <= 0.10 else "Confirm whether the change is recurring, then update the overhead estimate in Settings.",
        })
    return {
        "status": "review_required" if any(item["severity"] in {"warn", "bad"} for item in findings) else "matched",
        "summary": f"Compared the bill with {context.get('estimate_name') or 'the selected company estimate'}.",
        "extracted": extracted,
        "metrics": [{"label": "Amount due", "observed": observed, "expected": expected}],
        "findings": findings,
    }
