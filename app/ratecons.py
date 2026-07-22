from __future__ import annotations

import hashlib
import io
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from pypdf import PdfReader

from .money import MoneyInputError, money_to_cents


MAX_RATECON_BYTES = 12 * 1024 * 1024
MAX_RATECON_PAGES = 25
ALLOWED_RATECON_TYPES = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
}
MATERIAL_CLASSIFICATIONS = frozenset(
    {"FINANCIAL_DIFFERENCE", "OPERATIONAL_CONFLICT", "REVIEW_REQUIRED"}
)


class RateConError(ValueError):
    pass


class StorageConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ValidatedUpload:
    media_type: str
    extension: str
    size_bytes: int
    sha256: str
    page_count: int


@dataclass(frozen=True)
class MalwareScanResult:
    status: str
    provider: str
    detail: str = ""


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: str
    confidence: float
    page: int | None
    evidence: str
    bounding_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExtractionResult:
    fields: tuple[ExtractedField, ...]
    provider: str
    provider_version: str
    status: str
    detail: str = ""

    def values(self) -> dict[str, str]:
        return {field.name: field.value for field in self.fields}


@dataclass(frozen=True)
class RateConDifference:
    field_name: str
    booked_value: str
    ratecon_value: str
    classification: str
    financial_impact_cents: int | None
    operational_impact: str
    confidence: float
    evidence: str

    @property
    def material(self) -> bool:
        return self.classification in MATERIAL_CLASSIFICATIONS

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"material": self.material}


@dataclass(frozen=True)
class MatchCandidate:
    load_id: int
    public_uuid: str
    load_number: str
    score: int
    reasons: tuple[str, ...]


class ObjectStorageProvider(Protocol):
    name: str
    secure_at_rest: bool

    def put(self, key: str, payload: bytes, *, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class MalwareScanProvider(Protocol):
    name: str

    def scan(self, payload: bytes, *, filename: str) -> MalwareScanResult: ...


class OcrProvider(Protocol):
    name: str
    version: str

    def text(self, payload: bytes, *, media_type: str) -> str: ...


class DocumentExtractionProvider(Protocol):
    name: str
    version: str

    def extract(self, text_by_page: Sequence[str]) -> ExtractionResult: ...


def _safe_key(key: str) -> Path:
    parts = Path(str(key or "").replace("\\", "/")).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise RateConError("Invalid private object key")
    return Path(*parts)


class LocalPrivateStorageProvider:
    """Private local-volume adapter; production requires an encrypted managed volume."""

    name = "private_local_volume"

    def __init__(self, root: Path, *, secure_at_rest: bool = False):
        self.root = root.resolve()
        self.secure_at_rest = secure_at_rest

    def _path(self, key: str) -> Path:
        target = (self.root / _safe_key(key)).resolve()
        if self.root != target and self.root not in target.parents:
            raise RateConError("Private object key escaped its storage root")
        return target

    def put(self, key: str, payload: bytes, *, content_type: str) -> None:
        del content_type
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        target = self._path(key)
        if target.exists():
            target.unlink()


class InMemoryObjectStorageProvider:
    name = "memory"
    secure_at_rest = True

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, payload: bytes, *, content_type: str) -> None:
        del content_type
        self.objects[str(_safe_key(key))] = bytes(payload)

    def get(self, key: str) -> bytes:
        return self.objects[str(_safe_key(key))]

    def delete(self, key: str) -> None:
        self.objects.pop(str(_safe_key(key)), None)


class ManualMalwareScanProvider:
    name = "manual"

    def scan(self, payload: bytes, *, filename: str) -> MalwareScanResult:
        del payload, filename
        return MalwareScanResult(
            "PENDING_MANUAL", self.name, "No malware scanner is configured; dispatch review stays blocked."
        )


class MockMalwareScanProvider:
    name = "mock"

    def __init__(self, *, clean: bool = True):
        self.clean = clean

    def scan(self, payload: bytes, *, filename: str) -> MalwareScanResult:
        del payload, filename
        return MalwareScanResult("CLEAN" if self.clean else "REJECTED", self.name)


class ManualOcrProvider:
    name = "manual"
    version = "1"

    def text(self, payload: bytes, *, media_type: str) -> str:
        del payload, media_type
        return ""


class MockOcrProvider:
    name = "mock_ocr"
    version = "1"

    def __init__(self, text: str):
        self.value = text

    def text(self, payload: bytes, *, media_type: str) -> str:
        del payload, media_type
        return self.value


FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
    "broker_customer": (r"(?:broker|customer)\s*[:#-]?\s*([^\n]{2,100})",),
    "load_number": (r"(?:load|shipment)\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{3,40})",),
    "ratecon_number": (r"(?:rate\s*confirmation|ratecon)\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{3,40})",),
    "total_rate": (r"(?:total\s*(?:rate|charges?)|all[- ]in\s*rate)\s*[:$ ]+([0-9][0-9,]*\.?[0-9]{0,2})",),
    "pickup_date": (r"(?:pickup|pick up)\s*(?:date)?\s*[:#-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",),
    "delivery_date": (r"(?:delivery|deliver)\s*(?:date)?\s*[:#-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",),
    "tracking_penalty": (r"((?:tracking|check[- ]?call)[^\n]{0,100}(?:penalty|deduct|charge)[^\n]{0,60})",),
    "driver_assist": (r"((?:driver assist|driver load|driver unload)[^\n]{0,100})",),
    "factoring_restriction": (r"((?:no factoring|factoring prohibited|do not factor)[^\n]{0,100})",),
}


class BasicRateConExtractionProvider:
    """Conservative label extraction for digital PDFs; no AI and no invented values."""

    name = "carrieros_basic_labels"
    version = "1"

    def extract(self, text_by_page: Sequence[str]) -> ExtractionResult:
        fields: list[ExtractedField] = []
        for field_name, patterns in FIELD_PATTERNS.items():
            found = False
            for page_number, text in enumerate(text_by_page, 1):
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if not match:
                        continue
                    evidence = " ".join(match.group(0).split())[:240]
                    value = " ".join(match.group(1).split()).strip(" :#-")
                    fields.append(
                        ExtractedField(field_name, value, 0.75, page_number, evidence)
                    )
                    found = True
                    break
                if found:
                    break
        status = "EXTRACTED" if fields else "MANUAL_REVIEW"
        detail = "" if fields else "No supported labels were found; enter the RateCon facts manually."
        return ExtractionResult(tuple(fields), self.name, self.version, status, detail)


class MockDocumentExtractionProvider:
    name = "mock_extraction"
    version = "1"

    def __init__(self, fields: Sequence[ExtractedField]):
        self.fields = tuple(fields)

    def extract(self, text_by_page: Sequence[str]) -> ExtractionResult:
        del text_by_page
        return ExtractionResult(self.fields, self.name, self.version, "EXTRACTED")


def validate_ratecon_upload(
    payload: bytes, *, filename: str, claimed_content_type: str
) -> ValidatedUpload:
    if not payload:
        raise RateConError("The RateCon file is empty")
    if len(payload) > MAX_RATECON_BYTES:
        raise RateConError(f"RateCon files are limited to {MAX_RATECON_BYTES // (1024 * 1024)} MB")
    media_type = str(claimed_content_type or "").split(";", 1)[0].strip().lower()
    if payload.startswith(b"%PDF-"):
        detected = "application/pdf"
    elif payload.startswith(b"\xff\xd8\xff"):
        detected = "image/jpeg"
    elif payload.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "image/png"
    else:
        raise RateConError("Upload a valid PDF, JPEG, or PNG RateCon")
    if media_type and media_type not in {detected, "application/octet-stream"}:
        raise RateConError("The file contents do not match the reported file type")
    pages = 1
    if detected == "application/pdf":
        try:
            pages = len(PdfReader(io.BytesIO(payload)).pages)
        except Exception as exc:
            raise RateConError("The PDF is damaged, encrypted, or unreadable") from exc
        if pages < 1 or pages > MAX_RATECON_PAGES:
            raise RateConError(f"RateCon PDFs are limited to {MAX_RATECON_PAGES} pages")
    return ValidatedUpload(
        detected,
        ALLOWED_RATECON_TYPES[detected],
        len(payload),
        hashlib.sha256(payload).hexdigest(),
        pages,
    )


def document_text_pages(payload: bytes, media_type: str, ocr: OcrProvider) -> list[str]:
    if media_type == "application/pdf":
        reader = PdfReader(io.BytesIO(payload))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        if any(pages):
            return pages
    text = ocr.text(payload, media_type=media_type).strip()
    return [text] if text else []


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _date_only(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"):
        try:
            return datetime.strptime(raw[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return raw[:10]


def suggest_ratecon_matches(
    loads: Sequence[Mapping[str, Any]], fields: Mapping[str, str]
) -> list[MatchCandidate]:
    rows: list[MatchCandidate] = []
    for load in loads:
        score = 0
        reasons: list[str] = []
        if fields.get("load_number") and _normalized(fields["load_number"]) == _normalized(load.get("load_number")):
            score += 50
            reasons.append("load number")
        if fields.get("broker_customer") and _normalized(fields["broker_customer"]) in _normalized(load.get("broker")):
            score += 15
            reasons.append("broker/customer")
        if fields.get("pickup_date") and _date_only(fields["pickup_date"]) == _date_only(load.get("pickup_date")):
            score += 10
            reasons.append("pickup date")
        if fields.get("delivery_date") and _date_only(fields["delivery_date"]) == _date_only(load.get("delivery_date")):
            score += 10
            reasons.append("delivery date")
        if fields.get("total_rate"):
            try:
                observed = money_to_cents(fields["total_rate"], field="RateCon total")
                booked = money_to_cents(load.get("final_agreed_rate") or load.get("revenue") or 0, field="Booked rate")
                if observed == booked:
                    score += 20
                    reasons.append("rate")
            except MoneyInputError:
                pass
        if score:
            rows.append(
                MatchCandidate(
                    int(load["id"]), str(load.get("public_uuid") or ""),
                    str(load.get("load_number") or ""), score, tuple(reasons)
                )
            )
    return sorted(rows, key=lambda item: (-item.score, item.load_number.casefold()))


def compare_ratecon_to_booking(
    booking: Mapping[str, Any], extracted: Sequence[ExtractedField]
) -> list[RateConDifference]:
    fields = {field.name: field for field in extracted}
    results: list[RateConDifference] = []

    def add(
        name: str,
        booked: Any,
        ratecon: Any,
        classification: str,
        impact: str,
        *,
        financial: int | None = None,
    ) -> None:
        field = fields.get(name)
        results.append(
            RateConDifference(
                name,
                str(booked or ""),
                str(ratecon or ""),
                classification,
                financial,
                impact,
                field.confidence if field else 1.0,
                field.evidence if field else "Human-entered review value",
            )
        )

    if "total_rate" in fields:
        try:
            booked_cents = money_to_cents(
                booking.get("final_agreed_rate") or booking.get("revenue") or 0,
                field="Booked rate",
            )
            ratecon_cents = money_to_cents(fields["total_rate"].value, field="RateCon total")
            delta = ratecon_cents - booked_cents
            add(
                "total_rate",
                f"{booked_cents / 100:.2f}",
                f"{ratecon_cents / 100:.2f}",
                "MATCH" if delta == 0 else "FINANCIAL_DIFFERENCE",
                "No rate change" if delta == 0 else "RateCon total differs from the agreed rate",
                financial=delta,
            )
        except MoneyInputError:
            add("total_rate", booking.get("final_agreed_rate"), fields["total_rate"].value, "REVIEW_REQUIRED", "Rate could not be parsed")

    comparisons = (
        ("broker_customer", booking.get("broker"), "MINOR_DIFFERENCE", "Broker/customer name differs"),
        ("load_number", booking.get("load_number"), "MINOR_DIFFERENCE", "Load identifier differs"),
        ("pickup_date", booking.get("pickup_date"), "OPERATIONAL_CONFLICT", "Pickup appointment changed"),
        ("delivery_date", booking.get("delivery_date"), "OPERATIONAL_CONFLICT", "Delivery appointment changed"),
    )
    for name, booked, mismatch, impact in comparisons:
        field = fields.get(name)
        if not field:
            continue
        same = (
            _date_only(booked) == _date_only(field.value)
            if name.endswith("_date")
            else _normalized(booked) == _normalized(field.value)
        )
        add(name, booked, field.value, "MATCH" if same else mismatch, "No difference" if same else impact)

    flags = (
        ("added_stop", "OPERATIONAL_CONFLICT", "RateCon adds an unpaid or unplanned stop"),
        ("tracking_penalty", "OPERATIONAL_CONFLICT", "RateCon adds a tracking or check-call penalty"),
        ("driver_assist", "OPERATIONAL_CONFLICT", "RateCon adds driver-assist work"),
        ("factoring_restriction", "FINANCIAL_DIFFERENCE", "RateCon restricts factoring or payment options"),
    )
    for name, classification, impact in flags:
        field = fields.get(name)
        if field and _normalized(field.value) not in {"", "0", "false", "no", "none"}:
            add(name, "Not in booking snapshot", field.value, classification, impact)
    return results


def configured_storage_provider() -> ObjectStorageProvider:
    configured_root = os.getenv("CARRIEROS_PRIVATE_STORAGE_ROOT", "").strip()
    database_path = Path(os.getenv("CARRIEROS_DB", "carrieros_v02.db")).resolve()
    root = Path(configured_root) if configured_root else database_path.parent / "private-documents"
    encrypted = os.getenv("CARRIEROS_STORAGE_ENCRYPTED_AT_REST", "false").strip().lower() == "true"
    return LocalPrivateStorageProvider(root, secure_at_rest=encrypted)


def configured_malware_scan_provider() -> MalwareScanProvider:
    if os.getenv("CARRIEROS_MALWARE_SCANNER", "manual").strip().lower() == "mock-clean":
        return MockMalwareScanProvider()
    return ManualMalwareScanProvider()


def configured_ocr_provider() -> OcrProvider:
    return ManualOcrProvider()


def configured_extraction_provider() -> DocumentExtractionProvider:
    return BasicRateConExtractionProvider()


def extraction_json(result: ExtractionResult) -> str:
    return json.dumps(
        {
            "provider": result.provider,
            "provider_version": result.provider_version,
            "status": result.status,
            "detail": result.detail,
            "fields": [field.to_dict() for field in result.fields],
            "extracted_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def default_retention_date(days: int = 365 * 7) -> str:
    return date.fromordinal(date.today().toordinal() + max(1, days)).isoformat()
