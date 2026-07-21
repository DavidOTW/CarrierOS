from __future__ import annotations

import io
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import stripe
from docx import Document
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .calculations import (
    add_months,
    calculate_quote,
    driver_monthly_fixed,
    fuel_price_for,
    monday_for,
    parse_date,
    summarize_driver_period,
)
from .db import (
    as_dict,
    db_session,
    execute,
    hash_password,
    init_db,
    new_onboarding_token,
    query_all,
    query_one,
    record_audit_event,
    utc_now_iso,
    verify_password,
)
from .services import get_bundle, get_state, loads_with_results, selected_month
from .stripe_billing import (
    BillingConfigurationError,
    construct_webhook_event,
    create_checkout_session,
    create_portal_session,
    first_subscription_price_id,
    object_value,
    plan_code_for_price,
    price_id_for_plan,
    stripe_configured,
    unix_date,
)

BASE_DIR = Path(__file__).resolve().parent
VERSION = "0.7.0-beta"
ENVIRONMENT = os.getenv("CARRIEROS_ENV", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT == "production"
CANONICAL_BASE_URL = os.getenv(
    "CARRIEROS_CANONICAL_URL", "https://otwcarrieros.com"
).strip().rstrip("/")
SESSION_SECRET = os.getenv("CARRIEROS_SECRET", "")
if IS_PRODUCTION and len(SESSION_SECRET) < 32:
    raise RuntimeError("CARRIEROS_SECRET must be at least 32 characters in production.")
SESSION_SECRET = SESSION_SECRET or "development-only-change-me-v04"
BILLING_MODE = os.getenv("CARRIEROS_BILLING_MODE", "stripe").strip().lower()
if BILLING_MODE not in {"stripe", "beta"}:
    raise RuntimeError("CARRIEROS_BILLING_MODE must be 'stripe' or 'beta'.")
TRIAL_DAYS = 14
TERMS_VERSION = "2026-07-21"
SUPPORT_EMAIL = os.getenv(
    "CARRIEROS_SUPPORT_EMAIL", "david@outsidethewirelogistics.com"
).strip().lower()

PLAN_LIMITS = {
    "owner_operator": {"name": "Owner-Operator", "units": 2, "price": 25},
    "starter_fleet": {"name": "Starter Fleet", "units": 5, "price": 50},
    "small_fleet": {"name": "Small Fleet", "units": 10, "price": 75},
    "growing_fleet": {"name": "Growing Fleet", "units": 20, "price": 100},
}

SEO_PAGES = {
    "small-fleet-trucking-software": {
        "title": "Small Fleet Trucking Software | CarrierOS",
        "description": "Small fleet trucking software for owner-operators and carriers with 1–20 trucks. Connect dispatch, driver pay, settlements, expenses, and profit per load.",
        "eyebrow": "Small fleet trucking software",
        "heading": "Run a small trucking fleet without running it from five spreadsheets.",
        "lead": "CarrierOS gives owner-operators and small carrier teams one browser-based workspace for loads, driver pay, operating costs, receivables, and the profit each load actually keeps.",
        "audience": "Built for owner-operators growing beyond one truck, fleet owners managing 2–20 power units, and the dispatch or office people keeping those operations moving.",
        "problem_title": "A practical operating system for the part of the market enterprise TMS platforms overlook.",
        "problem_copy": "Small fleets need more than a load list, but they should not need enterprise software, dedicated IT staff, or a long implementation. CarrierOS keeps the daily operating picture focused on the decisions that affect cash and margin.",
        "benefits": [
            ("Dispatch and load control", "Keep lanes, dates, drivers, units, revenue, miles, and load status connected."),
            ("Driver pay flexibility", "Use profit split, percent of revenue, per mile, flat rate, hourly, day rate, or salary by driver."),
            ("Profit per load", "Compare revenue with fuel, driver pay, maintenance, direct costs, fixed costs, and overhead."),
            ("Carrier administration", "Track receivables, detention, compliance dates, onboarding records, and operating documents."),
        ],
        "workflow_title": "From booked load to a clearer carrier result",
        "workflow": [
            ("Enter the load", "Record the lane, dates, miles, revenue, assigned driver, and power unit."),
            ("Apply your real costs", "CarrierOS uses your fuel, maintenance, fixed-cost, fee, and driver-pay assumptions."),
            ("Review the result", "See estimated carrier profit, margin, driver obligation, and the items that need attention."),
        ],
        "faqs": [
            ("Who is CarrierOS built for?", "Owner-operators and small U.S. motor carriers that want a clearer view of dispatch, driver pay, and profitability without enterprise complexity."),
            ("Does CarrierOS replace my ELD or accounting system?", "No. CarrierOS is an operations and profitability workspace. It does not replace an ELD, payroll provider, tax professional, or regulated accounting system."),
            ("Can office users and drivers be added?", "Plans are based on active power units and include unlimited driver records and office users."),
        ],
    },
    "driver-settlement-software": {
        "title": "Driver Settlement Software for Small Fleets | CarrierOS",
        "description": "Driver settlement software for small trucking fleets. Calculate seven driver pay structures, record payments, and keep load pay and carrier profit connected.",
        "eyebrow": "Driver settlement software",
        "heading": "Driver pay that follows the agreement—not a one-size-fits-all formula.",
        "lead": "CarrierOS helps small carriers calculate, review, and track driver pay across seven compensation structures while keeping the load economics visible.",
        "audience": "For carrier owners, dispatchers, and back-office teams paying company drivers, contractors, and owner-operators under different agreements.",
        "problem_title": "Make every settlement easier to explain and repeat.",
        "problem_copy": "Mixed pay arrangements become fragile when the math lives in memory or separate spreadsheets. CarrierOS keeps each driver's method attached to the operating record so pay and carrier margin can be reviewed together.",
        "benefits": [
            ("Profit split", "Calculate the agreed driver share after the allowed load costs in your operating model."),
            ("Mileage and flat pay", "Support per-mile rates or a fixed amount for a load or trip."),
            ("Revenue percentage", "Calculate driver pay as an agreed percentage of gross load revenue."),
            ("Time-based compensation", "Support hourly, day-rate, and salary-based settlement reporting."),
        ],
        "workflow_title": "A consistent driver-pay workflow",
        "workflow": [
            ("Choose the driver's model", "Set the compensation structure and rate that match the operating agreement."),
            ("Connect pay to the load", "Use the load's revenue, miles, dates, and allowed costs to calculate the obligation."),
            ("Track what was paid", "Record payments against cumulative driver or contractor balances for a clearer audit trail."),
        ],
        "faqs": [
            ("Which driver pay methods are supported?", "Profit split, per mile, flat rate, percent of revenue, hourly, day rate, and salary."),
            ("Can different drivers use different pay models?", "Yes. CarrierOS keeps compensation settings driver-specific, so a fleet can use mixed models."),
            ("Is CarrierOS a payroll processor?", "No. CarrierOS calculates and tracks operating pay obligations; it does not file payroll taxes or replace professional payroll, tax, legal, or accounting advice."),
        ],
    },
    "load-profitability-calculator": {
        "title": "Truck Load Profitability Calculator | CarrierOS",
        "description": "Calculate truck load profitability using revenue, miles, fuel, driver pay, maintenance, fixed costs, fees, and overhead. Try the free CarrierOS live demo.",
        "eyebrow": "Truck load profitability calculator",
        "heading": "Know what a load can keep—not only what it pays per mile.",
        "lead": "CarrierOS turns a load's rate, miles, fuel, driver pay, direct costs, fixed costs, and company assumptions into a clearer estimate of carrier profit and margin.",
        "audience": "For owner-operators, dispatchers, and small fleet owners comparing freight opportunities or reviewing completed load performance.",
        "problem_title": "Rate per mile is useful. It is not the whole profit story.",
        "problem_copy": "Two loads with the same rate per mile can produce different results after deadhead, fuel, driver compensation, maintenance, fixed-cost days, fees, and overhead. CarrierOS keeps those inputs together so the tradeoff is visible before or after booking.",
        "benefits": [
            ("Cost-based lane quotes", "Estimate break-even, target, and opening quote from your operating assumptions."),
            ("Fuel and maintenance", "Apply fuel price, MPG, maintenance reserve, and total-mile assumptions."),
            ("Driver pay", "Compare the effect of the driver's actual compensation model on the load result."),
            ("Carrier margin", "See estimated profit dollars and margin instead of relying on gross revenue alone."),
        ],
        "workflow_title": "Turn a rate confirmation into a decision",
        "workflow": [
            ("Enter the freight economics", "Add rate, loaded and empty miles, dates, and direct load expenses."),
            ("Apply company assumptions", "Use the unit, driver, fuel, maintenance, fees, fixed costs, and overhead that fit your operation."),
            ("Compare the outcome", "Review break-even, target quote, driver pay, carrier profit, and margin before relying on the number."),
        ],
        "faqs": [
            ("What costs should be included in load profitability?", "CarrierOS can model fuel, driver or contractor pay, maintenance, direct load costs, fixed costs, company fees, and overhead using the assumptions you enter."),
            ("Can I use the calculator before booking a load?", "Yes. The lane quote tool is designed to compare break-even, target, and opening quote values before a load is accepted."),
            ("Are the calculated results financial advice?", "No. Results are operational estimates based on user-entered assumptions and should be reviewed before business, tax, accounting, payroll, or compliance decisions."),
        ],
    },
}

INDEXABLE_PATHS = {"/", "/demo", *(f"/{slug}" for slug in SEO_PAGES)}
PUBLIC_CRAWL_FILES = {"/robots.txt", "/sitemap.xml"}
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_ATTEMPTS = 10
SIGNUP_WINDOW_SECONDS = 60 * 60
SIGNUP_MAX_ATTEMPTS = 5
login_attempts: dict[str, list[float]] = {}
signup_attempts: dict[str, list[float]] = {}

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CarrierOS", version=VERSION, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="carrieros_session",
    same_site="lax",
    https_only=IS_PRODUCTION,
    max_age=60 * 60 * 12,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        if request.method == "GET" and (path in INDEXABLE_PATHS or path in PUBLIC_CRAWL_FILES):
            response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=3600"
        elif not path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        if path not in INDEXABLE_PATHS and path not in PUBLIC_CRAWL_FILES and not path.startswith("/static/"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        production_upgrade = "; upgrade-insecure-requests" if IS_PRODUCTION else ""
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; font-src 'self'; frame-ancestors 'none'; "
            f"base-uri 'self'; form-action 'self'{production_upgrade}"
        )
        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def number(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def optional_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def integer(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def yes(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "yes", "true", "on"}


def percent(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "0.0%"


def current_user(request: Request) -> dict[str, Any] | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    row = query_one(
        """SELECT u.*, o.name AS organization_name, o.owner_name, o.owner_email,
        o.source_filename, o.source_sync_date, o.plan_code, o.active_unit_limit,
        o.subscription_status, o.trial_ends_at, o.billing_customer_reference,
        o.billing_subscription_reference, o.billing_price_reference,
        o.subscription_current_period_end, o.subscription_cancel_at_period_end
        FROM users u JOIN organizations o ON o.id=u.organization_id WHERE u.id=?""",
        (user_id,),
    )
    return as_dict(row)


def subscription_allows_access(user: dict[str, Any]) -> bool:
    status = str(user.get("subscription_status") or "").lower()
    if status == "active":
        return True
    if status != "trialing":
        return False
    trial_end = parse_date(user.get("trial_ends_at"))
    return bool(trial_end and trial_end >= date.today())


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if not subscription_allows_access(user):
        raise HTTPException(status_code=402, detail="Subscription required")
    return user


def render(request: Request, name: str, context: dict[str, Any] | None = None, status_code: int = 200):
    context = context or {}
    csrf_token = request.session.get("csrf_token")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = csrf_token
    context.update({
        "request": request,
        "user": current_user(request),
        "money": money,
        "percent": percent,
        "today": date.today(),
        "version": VERSION,
        "support_email": SUPPORT_EMAIL,
        "billing_mode": BILLING_MODE,
        "csrf_token": csrf_token,
        "flash": request.session.pop("flash", None) if hasattr(request, "session") else None,
    })
    return templates.TemplateResponse(request=request, name=name, context=context, status_code=status_code)


def seo_context(
    path: str,
    title: str,
    description: str,
    *,
    page_type: str = "WebPage",
    faqs: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    canonical_url = f"{CANONICAL_BASE_URL}{path}"
    graph: list[dict[str, Any]] = [
        {
            "@type": "Organization",
            "@id": f"{CANONICAL_BASE_URL}/#organization",
            "name": "Outside The Wire Logistics LLC",
            "url": "https://www.outsidethewirelogistics.com/",
            "email": SUPPORT_EMAIL,
            "brand": {"@type": "Brand", "name": "CarrierOS"},
        },
        {
            "@type": page_type,
            "@id": f"{canonical_url}#webpage",
            "url": canonical_url,
            "name": title,
            "description": description,
            "inLanguage": "en-US",
            "isPartOf": {"@id": f"{CANONICAL_BASE_URL}/#website"},
            "publisher": {"@id": f"{CANONICAL_BASE_URL}/#organization"},
        },
        {
            "@type": "WebSite",
            "@id": f"{CANONICAL_BASE_URL}/#website",
            "url": f"{CANONICAL_BASE_URL}/",
            "name": "CarrierOS",
            "description": "Fleet operations and profitability software for owner-operators and small motor carriers.",
            "publisher": {"@id": f"{CANONICAL_BASE_URL}/#organization"},
        },
    ]
    if path == "/":
        graph.append(
            {
                "@type": "WebApplication",
                "@id": f"{CANONICAL_BASE_URL}/#software",
                "name": "CarrierOS",
                "url": f"{CANONICAL_BASE_URL}/",
                "applicationCategory": "BusinessApplication",
                "applicationSubCategory": "Trucking management software",
                "operatingSystem": "Any operating system with a modern web browser",
                "browserRequirements": "Requires JavaScript and a modern web browser",
                "description": description,
                "featureList": [
                    "Dispatch and load tracking",
                    "Seven driver compensation structures",
                    "Driver settlement tracking",
                    "Load profitability calculations",
                    "Cost-based freight lane quotes",
                    "Receivables and detention tracking",
                ],
                "audience": {
                    "@type": "BusinessAudience",
                    "audienceType": "Owner-operators and small motor carriers with 1 to 20 power units",
                },
                "provider": {"@id": f"{CANONICAL_BASE_URL}/#organization"},
                "offers": [
                    {
                        "@type": "Offer",
                        "name": plan["name"],
                        "price": plan["price"],
                        "priceCurrency": "USD",
                        "description": f"Up to {plan['units']} active power units; unlimited driver records and office users.",
                        "url": f"{CANONICAL_BASE_URL}/signup?plan={code}",
                    }
                    for code, plan in PLAN_LIMITS.items()
                ],
            }
        )
    if faqs:
        graph.append(
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": question,
                        "acceptedAnswer": {"@type": "Answer", "text": answer},
                    }
                    for question, answer in faqs
                ],
            }
        )
    return {
        "seo_title": title,
        "seo_description": description,
        "canonical_url": canonical_url,
        "robots_content": "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1",
        "social_image_url": f"{CANONICAL_BASE_URL}/static/carrieros-launch-og.png",
        "structured_data": {"@context": "https://schema.org", "@graph": graph},
    }


async def verified_form(request: Request):
    form = await request.form()
    if not IS_PRODUCTION:
        return form
    expected = str(request.session.get("csrf_token") or "")
    supplied = str(form.get("_csrf") or "")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="Invalid form token")
    return form


def valid_password(password: str) -> bool:
    return (
        len(password) >= 12
        and any(char.islower() for char in password)
        and any(char.isupper() for char in password)
        and any(char.isdigit() for char in password)
        and any(not char.isalnum() for char in password)
    )


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def login_rate_limited(request: Request) -> bool:
    key = client_key(request)
    cutoff = time.time() - LOGIN_WINDOW_SECONDS
    recent = [stamp for stamp in login_attempts.get(key, []) if stamp >= cutoff]
    login_attempts[key] = recent
    return len(recent) >= LOGIN_MAX_ATTEMPTS


def signup_rate_limited(request: Request) -> bool:
    key = client_key(request)
    cutoff = time.time() - SIGNUP_WINDOW_SECONDS
    recent = [stamp for stamp in signup_attempts.get(key, []) if stamp >= cutoff]
    signup_attempts[key] = recent
    return len(recent) >= SIGNUP_MAX_ATTEMPTS


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


def public_url(request: Request) -> str:
    configured = os.getenv("CARRIEROS_PUBLIC_URL", "").strip().rstrip("/")
    if configured:
        return configured
    render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip().rstrip("/")
    if render_hostname:
        return f"https://{render_hostname}"
    if IS_PRODUCTION:
        raise BillingConfigurationError("CARRIEROS_PUBLIC_URL is not configured.")
    return str(request.base_url).rstrip("/")


def set_flash(request: Request, text: str) -> None:
    request.session["flash"] = text


def compliance_status(expiration_date: str | None) -> tuple[str, int | None]:
    exp = parse_date(expiration_date)
    if not expiration_date:
        return "Missing date", None
    if not exp:
        return "Invalid", None
    days = (exp - date.today()).days
    if days < 0:
        return "Expired", days
    if days <= 30:
        return "Due soon", days
    return "Current", days


def invoice_aging(row: Any) -> dict[str, Any]:
    data = dict(row)
    if row["paid_date"] or str(row["status"]).lower() == "paid":
        data["age_days"] = 0
        data["aging_label"] = "Paid"
        return data
    due = parse_date(row["due_date"])
    age = (date.today() - due).days if due else 0
    data["age_days"] = max(0, age)
    if age <= 0:
        data["aging_label"] = "Not due"
    elif age <= 30:
        data["aging_label"] = "1-30 days"
    elif age <= 60:
        data["aging_label"] = "31-60 days"
    elif age <= 90:
        data["aging_label"] = "61-90 days"
    else:
        data["aging_label"] = "90+ days"
    return data


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    return redirect("/login")


@app.exception_handler(402)
async def subscription_required_handler(request: Request, exc: HTTPException):
    return redirect("/billing")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/manifest.webmanifest")
def manifest() -> Response:
    return Response((BASE_DIR / "static" / "manifest.webmanifest").read_text(encoding="utf-8"), media_type="application/manifest+json")


@app.get("/service-worker.js")
def service_worker() -> Response:
    return Response((BASE_DIR / "static" / "service-worker.js").read_text(encoding="utf-8"), media_type="application/javascript")


@app.get("/robots.txt")
def robots() -> Response:
    blocked_paths = (
        "/billing",
        "/compliance",
        "/dashboard",
        "/detention/",
        "/documents",
        "/drivers",
        "/financials",
        "/fuel",
        "/health",
        "/idle",
        "/loads",
        "/onboard/",
        "/onboarding",
        "/payments",
        "/quotes",
        "/receivables",
        "/settings",
        "/stripe/",
        "/vehicles",
    )
    body = "User-agent: *\n" + "".join(f"Disallow: {path}\n" for path in blocked_paths)
    body += f"\nSitemap: {CANONICAL_BASE_URL}/sitemap.xml\n"
    return Response(body, media_type="text/plain")


@app.get("/sitemap.xml")
def sitemap() -> Response:
    updated = "2026-07-21"
    paths = ["/", "/demo", *(f"/{slug}" for slug in SEO_PAGES)]
    urls = "".join(
        f"<url><loc>{CANONICAL_BASE_URL}{path}</loc><lastmod>{updated}</lastmod></url>"
        for path in paths
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return Response(xml, media_type="application/xml")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    description = "Small fleet trucking software for owner-operators and carriers with 1–20 trucks. Manage dispatch, seven driver pay models, settlements, and profit per load."
    return render(
        request,
        "marketing.html",
        {
            "public_page": True,
            "plans": PLAN_LIMITS,
            **seo_context(
                "/",
                "Small Fleet Trucking Software | CarrierOS",
                description,
                page_type="WebPage",
            ),
        },
    )


@app.get("/demo", response_class=HTMLResponse)
def demo(request: Request):
    return render(
        request,
        "demo.html",
        {
            "public_page": True,
            "plans": PLAN_LIMITS,
            **seo_context(
                "/demo",
                "CarrierOS Live Demo | Small Fleet Trucking Software",
                "Try the CarrierOS live demo with fictional fleet data. Explore dispatch, seven driver pay structures, settlements, pricing, and profit per load.",
            ),
        },
    )


@app.get("/small-fleet-trucking-software", response_class=HTMLResponse)
@app.get("/driver-settlement-software", response_class=HTMLResponse)
@app.get("/load-profitability-calculator", response_class=HTMLResponse)
def seo_landing_page(request: Request):
    seo_slug = request.url.path.strip("/")
    page = SEO_PAGES.get(seo_slug)
    if not page:
        raise HTTPException(status_code=404, detail="Not found")
    return render(
        request,
        "seo_page.html",
        {
            "public_page": True,
            "page": page,
            "seo_slug": seo_slug,
            **seo_context(
                f"/{seo_slug}",
                page["title"],
                page["description"],
                faqs=page["faqs"],
            ),
        },
    )


@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return render(request, "privacy.html", {"public_page": True})


@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return render(
        request,
        "terms.html",
        {"public_page": True, "terms_version": TERMS_VERSION},
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if current_user(request):
        return redirect("/dashboard")
    return render(request, "login.html", {"public_page": True})


@app.post("/login")
async def login(request: Request):
    if login_rate_limited(request):
        return render(request, "login.html", {"error": "Too many sign-in attempts. Try again in 15 minutes.", "public_page": True}, 429)
    form = await verified_form(request)
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))
    row = query_one("SELECT * FROM users WHERE lower(email)=?", (email,))
    if not row or not verify_password(password, row["password_hash"]):
        login_attempts.setdefault(client_key(request), []).append(time.time())
        return render(request, "login.html", {
            "error": "Invalid email or password.",
            "public_page": True,
        }, 400)
    request.session.clear()
    request.session["user_id"] = row["id"]
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    login_attempts.pop(client_key(request), None)
    record_audit_event(
        "user.login",
        organization_id=int(row["organization_id"]),
        user_id=int(row["id"]),
    )
    return redirect("/dashboard")


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, plan: str = "owner_operator"):
    if current_user(request):
        return redirect("/dashboard")
    selected_plan = plan if plan in PLAN_LIMITS else "owner_operator"
    return render(request, "signup.html", {"plans": PLAN_LIMITS, "selected_plan": selected_plan, "public_page": True})


@app.post("/signup", response_class=HTMLResponse)
async def signup(request: Request):
    if signup_rate_limited(request):
        return render(request, "signup.html", {
            "error": "Too many accounts were created from this connection. Try again in one hour.",
            "plans": PLAN_LIMITS,
            "selected_plan": "owner_operator",
            "public_page": True,
        }, 429)
    form = await verified_form(request)
    full_name = str(form.get("full_name", "")).strip()
    company_name = str(form.get("company_name", "")).strip()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))
    accepted_terms = yes(form.get("accepted_terms"))
    plan_code = str(form.get("plan", "owner_operator"))
    if plan_code not in PLAN_LIMITS:
        plan_code = "owner_operator"
    plan = PLAN_LIMITS[plan_code]
    error = None
    if not full_name or not company_name or "@" not in email:
        error = "Enter your name, company, and a valid email address."
    elif not valid_password(password):
        error = "Use at least 12 characters with uppercase, lowercase, a number, and a symbol."
    elif not accepted_terms:
        error = "Accept the Terms of Service and Privacy Policy to create an account."
    elif query_one("SELECT id FROM users WHERE lower(email)=?", (email,)):
        error = "An account already exists for that email address."
    if error:
        return render(request, "signup.html", {
            "error": error,
            "plans": PLAN_LIMITS,
            "selected_plan": plan_code,
            "values": {"full_name": full_name, "company_name": company_name, "email": email},
            "public_page": True,
        }, 400)

    trial_ends_at = (date.today() + timedelta(days=TRIAL_DAYS)).isoformat() if BILLING_MODE == "beta" else None
    subscription_status = "trialing" if BILLING_MODE == "beta" else "incomplete"
    accepted_at = utc_now_iso()
    with db_session() as conn:
        org_id = conn.execute(
            """INSERT INTO organizations
            (name, owner_name, owner_email, plan_code, active_unit_limit,
             subscription_status, trial_ends_at, reporting_start_month, default_report_month,
             terms_accepted_at, terms_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                company_name, full_name, email, plan_code, int(plan["units"]),
                subscription_status, trial_ends_at,
                date.today().replace(day=1).isoformat(), date.today().replace(day=1).isoformat(),
                accepted_at, TERMS_VERSION,
            ),
        ).lastrowid
        user_id = conn.execute(
            "INSERT INTO users (organization_id, full_name, email, password_hash, is_admin) VALUES (?, ?, ?, ?, 1)",
            (org_id, full_name, email, hash_password(password)),
        ).lastrowid
        conn.execute(
            "INSERT INTO overhead_items (organization_id, name, monthly_cost, sort_order) VALUES (?, 'Other overhead', 0, 1)",
            (org_id,),
        )
    signup_attempts.setdefault(client_key(request), []).append(time.time())
    record_audit_event(
        "organization.created",
        organization_id=int(org_id),
        user_id=int(user_id),
        details={"billing_mode": BILLING_MODE, "plan_code": plan_code, "terms_version": TERMS_VERSION},
    )
    request.session.clear()
    request.session["user_id"] = user_id
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    return redirect("/dashboard" if BILLING_MODE == "beta" else "/billing?new=1")


@app.get("/billing", response_class=HTMLResponse)
def billing(request: Request, checkout: str | None = None, new: int = 0):
    user = current_user(request)
    if not user:
        return redirect("/login")
    plan = PLAN_LIMITS.get(str(user.get("plan_code")), PLAN_LIMITS["owner_operator"])
    return render(request, "billing.html", {
        "plan": plan,
        "plans": PLAN_LIMITS,
        "stripe_ready": stripe_configured(),
        "billing_mode": BILLING_MODE,
        "has_access": subscription_allows_access(user),
        "checkout_result": checkout,
        "new_account": bool(new),
    })


@app.post("/billing/checkout")
async def billing_checkout(request: Request):
    user = current_user(request)
    if not user:
        return redirect("/login")
    if BILLING_MODE == "beta":
        set_flash(request, "No payment is required during the founding beta.")
        return redirect("/billing")
    form = await verified_form(request)
    plan_code = str(form.get("plan", user.get("plan_code") or "owner_operator"))
    if plan_code not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Unknown plan")
    if user.get("billing_subscription_reference") and str(user.get("subscription_status")) not in {
        "canceled", "incomplete_expired"
    }:
        set_flash(request, "Use the secure billing portal to change an existing subscription.")
        return redirect("/billing")
    try:
        base_url = public_url(request)
        session = create_checkout_session(
            organization_id=int(user["organization_id"]),
            owner_email=str(user["owner_email"] or user["email"]),
            plan_code=plan_code,
            existing_customer_id=str(user["billing_customer_reference"] or "") or None,
            success_url=f"{base_url}/billing?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/billing?checkout=cancelled",
        )
    except BillingConfigurationError:
        set_flash(request, "Secure billing is not configured yet. Please contact support.")
        return redirect("/billing")
    except stripe.StripeError:
        set_flash(request, "Stripe could not start checkout. Please try again or contact support.")
        return redirect("/billing")
    checkout_url = str(object_value(session, "url") or "")
    if not checkout_url.startswith("https://"):
        set_flash(request, "Stripe did not return a secure checkout link. Please contact support.")
        return redirect("/billing")
    return redirect(checkout_url)


@app.post("/billing/portal")
async def billing_portal(request: Request):
    user = current_user(request)
    if not user:
        return redirect("/login")
    await verified_form(request)
    customer_id = str(user.get("billing_customer_reference") or "")
    if not customer_id:
        set_flash(request, "Start a subscription before opening the billing portal.")
        return redirect("/billing")
    try:
        session = create_portal_session(
            customer_id=customer_id,
            return_url=f"{public_url(request)}/billing",
        )
    except (BillingConfigurationError, stripe.StripeError):
        set_flash(request, "Stripe could not open the billing portal. Please try again or contact support.")
        return redirect("/billing")
    portal_url = str(object_value(session, "url") or "")
    if not portal_url.startswith("https://"):
        set_flash(request, "Stripe did not return a secure billing link. Please contact support.")
        return redirect("/billing")
    return redirect(portal_url)


def _stripe_metadata(obj: Any) -> dict[str, Any]:
    metadata = object_value(obj, "metadata") or {}
    return dict(metadata) if hasattr(metadata, "items") else {}


def _organization_for_stripe_object(conn: Any, obj: Any) -> Any:
    metadata = _stripe_metadata(obj)
    raw_org_id = metadata.get("carrieros_org_id") or object_value(obj, "client_reference_id")
    if str(raw_org_id or "").isdigit():
        row = conn.execute("SELECT * FROM organizations WHERE id=?", (int(raw_org_id),)).fetchone()
        if row:
            return row
    subscription_id = object_value(obj, "subscription") or object_value(obj, "id")
    if isinstance(subscription_id, str) and subscription_id.startswith("sub_"):
        row = conn.execute(
            "SELECT * FROM organizations WHERE billing_subscription_reference=?", (subscription_id,)
        ).fetchone()
        if row:
            return row
    customer_id = object_value(obj, "customer")
    if isinstance(customer_id, str):
        return conn.execute(
            "SELECT * FROM organizations WHERE billing_customer_reference=?", (customer_id,)
        ).fetchone()
    return None


def _apply_checkout_completed(conn: Any, checkout_session: Any) -> None:
    if str(object_value(checkout_session, "mode") or "") != "subscription":
        return
    organization = _organization_for_stripe_object(conn, checkout_session)
    metadata = _stripe_metadata(checkout_session)
    plan_code = str(metadata.get("carrieros_plan_code") or "")
    if not organization or plan_code not in PLAN_LIMITS:
        return
    customer_id = object_value(checkout_session, "customer")
    subscription_id = object_value(checkout_session, "subscription")
    plan = PLAN_LIMITS[plan_code]
    conn.execute(
        """UPDATE organizations SET plan_code=?, active_unit_limit=?, subscription_status='trialing',
        trial_ends_at=?, billing_customer_reference=COALESCE(?, billing_customer_reference),
        billing_subscription_reference=COALESCE(?, billing_subscription_reference),
        billing_price_reference=? WHERE id=?""",
        (
            plan_code,
            int(plan["units"]),
            (date.today() + timedelta(days=14)).isoformat(),
            customer_id,
            subscription_id,
            price_id_for_plan(plan_code),
            organization["id"],
        ),
    )


def _subscription_period_end(subscription: Any) -> str | None:
    direct = unix_date(object_value(subscription, "current_period_end"))
    if direct:
        return direct
    items = object_value(subscription, "items") or {}
    data = object_value(items, "data") or []
    return unix_date(object_value(data[0], "current_period_end")) if data else None


def _apply_subscription_event(conn: Any, subscription: Any, event_type: str) -> None:
    organization = _organization_for_stripe_object(conn, subscription)
    if not organization:
        return
    price_id = first_subscription_price_id(subscription)
    metadata = _stripe_metadata(subscription)
    plan_code = plan_code_for_price(price_id) or str(metadata.get("carrieros_plan_code") or "")
    if plan_code not in PLAN_LIMITS:
        plan_code = str(organization["plan_code"])
    plan = PLAN_LIMITS.get(plan_code, PLAN_LIMITS["owner_operator"])
    status = "canceled" if event_type == "customer.subscription.deleted" else str(
        object_value(subscription, "status") or organization["subscription_status"]
    )
    conn.execute(
        """UPDATE organizations SET plan_code=?, active_unit_limit=?, subscription_status=?,
        trial_ends_at=?, billing_customer_reference=COALESCE(?, billing_customer_reference),
        billing_subscription_reference=COALESCE(?, billing_subscription_reference),
        billing_price_reference=COALESCE(?, billing_price_reference),
        subscription_current_period_end=?, subscription_cancel_at_period_end=? WHERE id=?""",
        (
            plan_code,
            int(plan["units"]),
            status,
            unix_date(object_value(subscription, "trial_end")),
            object_value(subscription, "customer"),
            object_value(subscription, "id"),
            price_id,
            _subscription_period_end(subscription),
            1 if object_value(subscription, "cancel_at_period_end") else 0,
            organization["id"],
        ),
    )


def _apply_invoice_event(conn: Any, invoice: Any, event_type: str) -> None:
    organization = _organization_for_stripe_object(conn, invoice)
    if not organization:
        return
    subscription_id = object_value(invoice, "subscription")
    if not subscription_id:
        parent = object_value(invoice, "parent") or {}
        details = object_value(parent, "subscription_details") or {}
        subscription_id = object_value(details, "subscription")
    if not subscription_id or subscription_id != organization["billing_subscription_reference"]:
        return
    status = "active" if event_type == "invoice.paid" else "past_due"
    conn.execute(
        "UPDATE organizations SET subscription_status=? WHERE id=?",
        (status, organization["id"]),
    )


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    try:
        event = construct_webhook_event(payload, request.headers.get("stripe-signature"))
    except BillingConfigurationError:
        return JSONResponse({"detail": "Webhook is not configured"}, status_code=503)
    except Exception:
        return JSONResponse({"detail": "Invalid webhook"}, status_code=400)

    event_id = str(object_value(event, "id") or "")
    event_type = str(object_value(event, "type") or "")
    data = object_value(event, "data") or {}
    stripe_object = object_value(data, "object") or {}
    if not event_id or not event_type:
        return JSONResponse({"detail": "Invalid event"}, status_code=400)

    with db_session() as conn:
        if conn.execute(
            "SELECT 1 FROM processed_stripe_events WHERE event_id=?", (event_id,)
        ).fetchone():
            return {"received": True, "duplicate": True}
        if event_type == "checkout.session.completed":
            _apply_checkout_completed(conn, stripe_object)
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.trial_will_end",
        }:
            _apply_subscription_event(conn, stripe_object, event_type)
        elif event_type in {"invoice.paid", "invoice.payment_failed"}:
            _apply_invoice_event(conn, stripe_object, event_type)
        conn.execute(
            "INSERT INTO processed_stripe_events (event_id, event_type) VALUES (?, ?)",
            (event_id, event_type),
        )
    return {"received": True}


@app.get("/logout")
def logout(request: Request):
    user = current_user(request)
    if user:
        record_audit_event(
            "user.logout",
            organization_id=int(user["organization_id"]),
            user_id=int(user["id"]),
        )
    request.session.clear()
    return redirect("/login")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, month: str | None = None):
    user = require_user(request)
    settings = query_one("SELECT * FROM organizations WHERE id=?", (user["organization_id"],))
    report_month = selected_month(month, settings["default_report_month"] if settings else None)
    bundle, state = get_state(user["organization_id"], report_month)
    all_loads = loads_with_results(bundle, state)

    compliance_rows = query_all("SELECT * FROM compliance_items WHERE organization_id=? ORDER BY expiration_date", (user["organization_id"],))
    compliance = []
    due_count = 0
    for row in compliance_rows:
        item = dict(row)
        item["status"], item["days"] = compliance_status(row["expiration_date"])
        compliance.append(item)
        if item["status"] != "Current":
            due_count += 1
    invoice_rows = query_all("SELECT * FROM invoices WHERE organization_id=? ORDER BY due_date", (user["organization_id"],))
    invoices = [invoice_aging(row) for row in invoice_rows]
    unpaid_total = sum(number(row["amount"]) for row in invoice_rows if str(row["status"]).lower() != "paid")
    overdue_total = sum(number(row["amount"]) for row in invoices if str(row["status"]).lower() != "paid" and row["age_days"] > 0)

    return render(request, "dashboard.html", {
        "bundle": bundle,
        "state": state,
        "stats": state["summary"],
        "warnings": state["warnings"],
        "balances": state["driver_balances"],
        "loads": all_loads[:10],
        "month": report_month,
        "monthly": state["selected_month_financial"],
        "bridges": state["selected_month_bridges"],
        "compliance_due": due_count,
        "unpaid_total": unpaid_total,
        "overdue_total": overdue_total,
        "compliance": compliance[:5],
        "invoices": invoices[:5],
    })


@app.get("/loads", response_class=HTMLResponse)
def loads_page(request: Request):
    user = require_user(request)
    bundle, state = get_state(user["organization_id"])
    return render(request, "loads.html", {
        "loads": loads_with_results(bundle, state),
        "state": state,
    })


def load_form_context(org_id: int, values: dict[str, Any] | None = None, editing: bool = False):
    bundle = get_bundle(org_id)
    current_fuel = fuel_price_for(date.today(), bundle["weekly_fuel"], number(bundle["settings"]["fallback_diesel_price"]))
    return {
        "drivers": bundle["drivers"],
        "vehicles": bundle["vehicles"],
        "values": values or {
            "pickup_date": date.today().isoformat(),
            "delivery_date": date.today().isoformat(),
            "status": "Booked",
            "include_in_model": 1,
        },
        "current_fuel": current_fuel,
        "editing": editing,
    }


@app.get("/loads/new", response_class=HTMLResponse)
def new_load_page(request: Request):
    user = require_user(request)
    return render(request, "load_form.html", load_form_context(user["organization_id"]))


@app.post("/loads/new")
async def create_load(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    driver_id = integer(form.get("driver_id"))
    driver = query_one("SELECT * FROM drivers WHERE id=? AND organization_id=?", (driver_id, user["organization_id"]))
    if not driver:
        raise HTTPException(400, "Select a valid driver")
    vehicle_id = integer(form.get("vehicle_id")) or integer(driver["vehicle_id"])
    load_id = execute(
        """INSERT INTO loads
        (organization_id, load_number, pickup_date, delivery_date, driver_id, vehicle_id,
         broker, origin, destination, status, revenue, loaded_miles, deadhead_miles,
         fuel_override, tolls_misc, other_direct_costs, notes, include_in_model)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user["organization_id"], str(form.get("load_number", "")).strip() or f"LOAD-{datetime.now():%Y%m%d%H%M}",
            str(form.get("pickup_date", "")) or None, str(form.get("delivery_date", "")) or None,
            driver_id, vehicle_id or None, str(form.get("broker", "")).strip(), str(form.get("origin", "")).strip(),
            str(form.get("destination", "")).strip(), str(form.get("status", "Booked")), optional_number(form.get("revenue")),
            number(form.get("loaded_miles")), number(form.get("deadhead_miles")), optional_number(form.get("fuel_override")),
            number(form.get("tolls_misc")), number(form.get("other_direct_costs")), str(form.get("notes", "")).strip(),
            1 if yes(form.get("include_in_model")) else 0,
        ),
    )
    set_flash(request, "Load saved and the full model was recalculated.")
    return redirect(f"/loads/{load_id}")


@app.get("/loads/{load_id}/edit", response_class=HTMLResponse)
def edit_load_page(request: Request, load_id: int):
    user = require_user(request)
    row = query_one("SELECT * FROM loads WHERE id=? AND organization_id=?", (load_id, user["organization_id"]))
    if not row:
        raise HTTPException(404, "Load not found")
    return render(request, "load_form.html", load_form_context(user["organization_id"], dict(row), True))


@app.post("/loads/{load_id}/edit")
async def update_load(request: Request, load_id: int):
    user = require_user(request)
    form = await verified_form(request)
    driver_id = integer(form.get("driver_id"))
    driver = query_one("SELECT * FROM drivers WHERE id=? AND organization_id=?", (driver_id, user["organization_id"]))
    if not driver:
        raise HTTPException(400, "Select a valid driver")
    vehicle_id = integer(form.get("vehicle_id")) or integer(driver["vehicle_id"])
    with db_session() as conn:
        conn.execute(
            """UPDATE loads SET load_number=?,pickup_date=?,delivery_date=?,driver_id=?,vehicle_id=?,
            broker=?,origin=?,destination=?,status=?,revenue=?,loaded_miles=?,deadhead_miles=?,
            fuel_override=?,tolls_misc=?,other_direct_costs=?,notes=?,include_in_model=?
            WHERE id=? AND organization_id=?""",
            (
                str(form.get("load_number", "")).strip() or f"LOAD-{load_id}", str(form.get("pickup_date", "")) or None,
                str(form.get("delivery_date", "")) or None, driver_id, vehicle_id or None, str(form.get("broker", "")).strip(),
                str(form.get("origin", "")).strip(), str(form.get("destination", "")).strip(), str(form.get("status", "Booked")),
                optional_number(form.get("revenue")), number(form.get("loaded_miles")), number(form.get("deadhead_miles")),
                optional_number(form.get("fuel_override")), number(form.get("tolls_misc")), number(form.get("other_direct_costs")),
                str(form.get("notes", "")).strip(), 1 if yes(form.get("include_in_model")) else 0,
                load_id, user["organization_id"],
            ),
        )
    set_flash(request, "Load updated. Overlapping truck-day costs were recalculated across every included load.")
    return redirect(f"/loads/{load_id}")


@app.get("/loads/{load_id}", response_class=HTMLResponse)
def load_detail(request: Request, load_id: int):
    user = require_user(request)
    bundle, state = get_state(user["organization_id"])
    item = next((row for row in loads_with_results(bundle, state) if int(row["id"]) == load_id), None)
    if not item:
        raise HTTPException(404, "Load not found")
    payments = query_all(
        """SELECT p.*,d.name AS driver_name FROM payments p LEFT JOIN drivers d ON d.id=p.driver_id
        WHERE p.organization_id=? AND p.load_id=? ORDER BY p.paid_at DESC,p.id DESC""",
        (user["organization_id"], load_id),
    )
    return render(request, "load_detail.html", {"load": item, "payments": [dict(p) for p in payments]})


@app.get("/vehicles", response_class=HTMLResponse)
def vehicles_page(request: Request):
    user = require_user(request)
    rows = query_all("SELECT * FROM vehicles WHERE organization_id=? ORDER BY active DESC,name", (user["organization_id"],))
    return render(request, "vehicles.html", {
        "vehicles": [dict(r) for r in rows],
        "unit_limit": int(user.get("active_unit_limit") or 2),
    })


@app.post("/vehicles")
async def create_vehicle(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    active = 1 if yes(form.get("active", "on")) else 0
    if active:
        active_count = query_one(
            "SELECT COUNT(*) AS total FROM vehicles WHERE organization_id=? AND active=1",
            (user["organization_id"],),
        )
        if int(active_count["total"] if active_count else 0) >= int(user.get("active_unit_limit") or 2):
            set_flash(request, "Your plan's active-unit limit has been reached. Upgrade from Billing to add another active unit.")
            return redirect("/vehicles")
    try:
        execute(
            "INSERT INTO vehicles (organization_id,name,equipment_type,active) VALUES (?,?,?,?)",
            (user["organization_id"], str(form.get("name", "New unit")).strip(), str(form.get("equipment_type", "Truck")).strip(), active),
        )
    except Exception as exc:
        raise HTTPException(400, "That unit name already exists") from exc
    set_flash(request, "Unit added. Assign it on Driver & Equipment Setup.")
    return redirect("/vehicles")


@app.get("/drivers", response_class=HTMLResponse)
def drivers_page(request: Request):
    user = require_user(request)
    bundle, state = get_state(user["organization_id"])
    vehicles = {int(v["id"]): v for v in bundle["vehicles"]}
    drivers = []
    balances = {int(b["driver_id"]): b for b in state["driver_balances"]}
    for row in bundle["drivers"]:
        item = dict(row)
        item["vehicle"] = vehicles.get(int(row.get("vehicle_id") or 0))
        item["monthly_fixed"] = driver_monthly_fixed(row)
        item["balance"] = balances.get(int(row["id"]))
        drivers.append(item)
    return render(request, "drivers.html", {"drivers": drivers, "vehicles": bundle["vehicles"]})


@app.post("/drivers")
async def create_driver(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    driver_id = execute(
        """INSERT INTO drivers
        (organization_id,vehicle_id,name,email,phone,role,pay_model,equipment_type,
         fixed_cost_start,fixed_cost_end,truck_financing_monthly,auto_insurance_monthly,
         trailer_financing_monthly,trailer_insurance_monthly,other_fixed_monthly,mpg,
         maintenance_per_mile,driver_profit_split_pct,contractor_gross_split_pct,
         owner_operator_split_pct,flat_rate_per_load,pay_per_loaded_mile,
         pay_per_total_mile,day_rate,payroll_burden_applies,notes,active)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            user["organization_id"], integer(form.get("vehicle_id")) or None, str(form.get("name", "New driver")).strip(),
            str(form.get("email", "")).strip(), str(form.get("phone", "")).strip(), str(form.get("role", "Driver")),
            str(form.get("pay_model", "Profit Split")), str(form.get("equipment_type", "")).strip(),
            str(form.get("fixed_cost_start", "")) or None, str(form.get("fixed_cost_end", "")) or None,
            number(form.get("truck_financing_monthly")), number(form.get("auto_insurance_monthly")),
            number(form.get("trailer_financing_monthly")), number(form.get("trailer_insurance_monthly")),
            number(form.get("other_fixed_monthly")), number(form.get("mpg"), 10), number(form.get("maintenance_per_mile"), .20),
            number(form.get("driver_profit_split_pct")), number(form.get("contractor_gross_split_pct")),
            number(form.get("owner_operator_split_pct")), number(form.get("flat_rate_per_load")),
            number(form.get("pay_per_loaded_mile")), number(form.get("pay_per_total_mile")),
            number(form.get("day_rate")), 1 if yes(form.get("payroll_burden_applies")) else 0,
            str(form.get("notes", "")).strip(), 1 if yes(form.get("active", "on")) else 0,
        ),
    )
    set_flash(request, "Driver and equipment profile added.")
    return redirect(f"/drivers#driver-{driver_id}")


@app.post("/drivers/{driver_id}/update")
async def update_driver(request: Request, driver_id: int):
    user = require_user(request)
    form = await verified_form(request)
    with db_session() as conn:
        conn.execute(
            """UPDATE drivers SET vehicle_id=?,name=?,email=?,phone=?,role=?,pay_model=?,equipment_type=?,
            fixed_cost_start=?,fixed_cost_end=?,truck_financing_monthly=?,auto_insurance_monthly=?,
            trailer_financing_monthly=?,trailer_insurance_monthly=?,other_fixed_monthly=?,mpg=?,
            maintenance_per_mile=?,driver_profit_split_pct=?,contractor_gross_split_pct=?,
            owner_operator_split_pct=?,flat_rate_per_load=?,pay_per_loaded_mile=?,
            pay_per_total_mile=?,day_rate=?,payroll_burden_applies=?,notes=?,active=?
            WHERE id=? AND organization_id=?""",
            (
                integer(form.get("vehicle_id")) or None, str(form.get("name", "")).strip(), str(form.get("email", "")).strip(),
                str(form.get("phone", "")).strip(), str(form.get("role", "Driver")), str(form.get("pay_model", "Profit Split")),
                str(form.get("equipment_type", "")).strip(), str(form.get("fixed_cost_start", "")) or None,
                str(form.get("fixed_cost_end", "")) or None, number(form.get("truck_financing_monthly")),
                number(form.get("auto_insurance_monthly")), number(form.get("trailer_financing_monthly")),
                number(form.get("trailer_insurance_monthly")), number(form.get("other_fixed_monthly")),
                number(form.get("mpg"), 10), number(form.get("maintenance_per_mile"), .20),
                number(form.get("driver_profit_split_pct")), number(form.get("contractor_gross_split_pct")),
                number(form.get("owner_operator_split_pct")), number(form.get("flat_rate_per_load")),
                number(form.get("pay_per_loaded_mile")), number(form.get("pay_per_total_mile")),
                number(form.get("day_rate")), 1 if yes(form.get("payroll_burden_applies")) else 0,
                str(form.get("notes", "")).strip(), 1 if yes(form.get("active")) else 0,
                driver_id, user["organization_id"],
            ),
        )
    set_flash(request, "Driver setup updated. All load pay and fixed-cost results were recalculated.")
    return redirect(f"/drivers#driver-{driver_id}")


@app.get("/fuel", response_class=HTMLResponse)
def fuel_page(request: Request):
    user = require_user(request)
    bundle = get_bundle(user["organization_id"])
    current_week = monday_for(date.today())
    current_effective = fuel_price_for(date.today(), bundle["weekly_fuel"], number(bundle["settings"]["fallback_diesel_price"]))
    return render(request, "fuel.html", {
        "rows": list(reversed(bundle["weekly_fuel"])),
        "current_week": current_week,
        "current_effective": current_effective,
        "fallback": bundle["settings"]["fallback_diesel_price"],
    })


@app.post("/fuel")
async def save_fuel(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    week = parse_date(form.get("week_start"))
    if not week:
        raise HTTPException(400, "Enter a valid week-start date")
    week = monday_for(week)
    with db_session() as conn:
        conn.execute(
            """INSERT INTO weekly_fuel (organization_id,week_start,average_price,source_notes,entered_by)
            VALUES (?,?,?,?,?) ON CONFLICT(organization_id,week_start) DO UPDATE SET
            average_price=excluded.average_price,source_notes=excluded.source_notes,entered_by=excluded.entered_by""",
            (user["organization_id"], week.isoformat(), number(form.get("average_price")), str(form.get("source_notes", "")).strip(), str(form.get("entered_by", user["full_name"])).strip()),
        )
    set_flash(request, f"Diesel price saved for the week of {week:%b %d, %Y}. Loads were recalculated.")
    return redirect("/fuel")


@app.get("/payments", response_class=HTMLResponse)
def payments_page(request: Request):
    user = require_user(request)
    bundle, state = get_state(user["organization_id"])
    rows = query_all(
        """SELECT p.*,d.name AS driver_name,l.load_number FROM payments p
        LEFT JOIN drivers d ON d.id=p.driver_id LEFT JOIN loads l ON l.id=p.load_id
        WHERE p.organization_id=? ORDER BY p.paid_at DESC,p.id DESC""",
        (user["organization_id"],),
    )
    return render(request, "payments.html", {
        "payments": [dict(r) for r in rows],
        "drivers": bundle["drivers"],
        "loads": list(reversed(bundle["loads"])),
        "balances": state["driver_balances"],
        "owner": state["owner_pay"],
    })


@app.post("/payments")
async def add_payment(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    execute(
        """INSERT INTO payments
        (organization_id,driver_id,load_id,paid_at,payment_type,amount,method,reference,notes,
         counts_against_load_pay,include_in_reports)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            user["organization_id"], integer(form.get("driver_id")) or None, integer(form.get("load_id")) or None,
            str(form.get("paid_at", date.today().isoformat())), str(form.get("payment_type", "Regular payout")),
            number(form.get("amount")), str(form.get("method", "")).strip(), str(form.get("reference", "")).strip(),
            str(form.get("notes", "")).strip(), 1 if yes(form.get("counts_against_load_pay")) else 0,
            1 if yes(form.get("include_in_reports")) else 0,
        ),
    )
    set_flash(request, "Payment recorded. Driver balances were recalculated cumulatively.")
    return redirect("/payments")


@app.get("/quotes", response_class=HTMLResponse)
def quote_page(request: Request):
    user = require_user(request)
    bundle = get_bundle(user["organization_id"])
    current_fuel = fuel_price_for(date.today(), bundle["weekly_fuel"], number(bundle["settings"]["fallback_diesel_price"]))
    return render(request, "quotes.html", {
        "drivers": bundle["drivers"],
        "result": None,
        "defaults": {
            "pickup_date": date.today().isoformat(),
            "fuel_price": current_fuel,
            "trip_days": 1,
            "target_margin_pct": bundle["settings"]["target_margin_pct"],
        },
    })


@app.post("/quotes", response_class=HTMLResponse)
async def calculate_quote_page(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    bundle = get_bundle(user["organization_id"])
    driver = next((d for d in bundle["drivers"] if int(d["id"]) == integer(form.get("driver_id"))), None)
    pickup = parse_date(form.get("pickup_date"))
    if not driver or not pickup:
        raise HTTPException(400, "Select a driver and valid pickup date")
    result = calculate_quote(
        settings=bundle["settings"], driver=driver, pickup_date=pickup,
        loaded_miles=number(form.get("loaded_miles")), deadhead_miles=number(form.get("deadhead_miles")),
        trip_days=integer(form.get("trip_days"), 1), fuel_price=number(form.get("fuel_price")),
        tolls_misc=number(form.get("tolls_misc")), other_direct_costs=number(form.get("other_direct_costs")),
        quoted_revenue=optional_number(form.get("quoted_revenue")), target_margin_pct=number(form.get("target_margin_pct"), bundle["settings"]["target_margin_pct"]),
    )
    return render(request, "quotes.html", {
        "drivers": bundle["drivers"], "result": result, "submitted": dict(form), "selected_driver": driver,
        "defaults": {"pickup_date": pickup.isoformat(), "fuel_price": form.get("fuel_price"), "trip_days": form.get("trip_days"), "target_margin_pct": form.get("target_margin_pct")},
    })


@app.get("/financials", response_class=HTMLResponse)
def financials_page(request: Request):
    user = require_user(request)
    bundle, state = get_state(user["organization_id"])
    current_month = date.today().replace(day=1)
    current_week_start = monday_for(date.today())
    current_week_end = current_week_start + timedelta(days=6)
    current_month_end = add_months(current_month, 1) - timedelta(days=1)
    month_stats = summarize_driver_period(bundle["drivers"], bundle["loads"], state["load_results"], current_month, current_month_end)
    week_stats = summarize_driver_period(bundle["drivers"], bundle["loads"], state["load_results"], current_week_start, current_week_end)
    return render(request, "financials.html", {
        "rows": state["monthly_financials"],
        "owner": state["owner_pay"],
        "month_stats": month_stats,
        "week_stats": week_stats,
        "current_month": current_month,
        "current_week_start": current_week_start,
        "current_week_end": current_week_end,
        "settings": bundle["settings"],
        "monthly_overhead": state["summary"]["monthly_company_overhead"],
    })


@app.get("/idle", response_class=HTMLResponse)
def idle_page(request: Request, month: str | None = None):
    user = require_user(request)
    settings = query_one("SELECT default_report_month FROM organizations WHERE id=?", (user["organization_id"],))
    report_month = selected_month(month, settings["default_report_month"] if settings else None)
    bundle, state = get_state(user["organization_id"], report_month)
    return render(request, "idle.html", {
        "month": report_month,
        "bridges": state["selected_month_bridges"],
        "periods": list(reversed(state["idle_state"]["periods"])),
        "drivers": bundle["drivers"],
        "vehicles": bundle["vehicles"],
    })


@app.post("/idle")
async def add_idle_period(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    driver_id = integer(form.get("driver_id"))
    driver = query_one("SELECT * FROM drivers WHERE id=? AND organization_id=?", (driver_id, user["organization_id"]))
    if not driver:
        raise HTTPException(400, "Select a valid driver")
    vehicle_id = integer(form.get("vehicle_id")) or integer(driver["vehicle_id"])
    execute(
        """INSERT INTO idle_periods
        (organization_id,start_date,end_date,driver_id,vehicle_id,situation,include_in_model,notes)
        VALUES (?,?,?,?,?,?,?,?)""",
        (
            user["organization_id"], str(form.get("start_date", "")) or None, str(form.get("end_date", "")) or None,
            driver_id, vehicle_id or None, str(form.get("situation", "Company Responsibility")),
            1 if yes(form.get("include_in_model")) else 0, str(form.get("notes", "")).strip(),
        ),
    )
    month = str(form.get("start_date", ""))[:7]
    set_flash(request, "Idle/time-off period recorded. Load-covered days were excluded automatically.")
    return redirect(f"/idle?month={month}-01" if month else "/idle")


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    user = require_user(request)
    bundle = get_bundle(user["organization_id"])
    return render(request, "settings.html", {"settings": bundle["settings"], "overhead": bundle["overhead_items"]})


@app.post("/settings")
async def update_settings(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    with db_session() as conn:
        conn.execute(
            """UPDATE organizations SET name=?,owner_name=?,owner_email=?,fallback_diesel_price=?,
            processing_fee_pct=?,admin_fee_per_load=?,payroll_burden_pct=?,target_margin_pct=?,
            target_max_deadhead_pct=?,min_company_profit_per_mile=?,owner_distribution_pct=?,
            supported_start_date=?,supported_end_date=?,max_active_days=?,tax_reserve_pct=?,
            growth_reserve_pct=?,reporting_start_month=?,default_report_month=? WHERE id=?""",
            (
                str(form.get("name", "")).strip(), str(form.get("owner_name", "")).strip(), str(form.get("owner_email", "")).strip(),
                number(form.get("fallback_diesel_price")), number(form.get("processing_fee_pct")), number(form.get("admin_fee_per_load")),
                number(form.get("payroll_burden_pct")), number(form.get("target_margin_pct")), number(form.get("target_max_deadhead_pct")),
                number(form.get("min_company_profit_per_mile")), number(form.get("owner_distribution_pct")),
                str(form.get("supported_start_date", "")), str(form.get("supported_end_date", "")), integer(form.get("max_active_days"), 31),
                number(form.get("tax_reserve_pct")), number(form.get("growth_reserve_pct")), str(form.get("reporting_start_month", "")),
                str(form.get("default_report_month", "")), user["organization_id"],
            ),
        )
        for row in query_all("SELECT id FROM overhead_items WHERE organization_id=?", (user["organization_id"],)):
            conn.execute("UPDATE overhead_items SET monthly_cost=? WHERE id=? AND organization_id=?", (number(form.get(f"overhead_{row['id']}")), row["id"], user["organization_id"]))
    set_flash(request, "Assumptions and company overhead updated. The entire model was recalculated.")
    return redirect("/settings")


@app.post("/settings/overhead")
async def add_overhead(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    order = query_one("SELECT COALESCE(MAX(sort_order),0)+1 AS n FROM overhead_items WHERE organization_id=?", (user["organization_id"],))
    execute("INSERT INTO overhead_items (organization_id,name,monthly_cost,sort_order) VALUES (?,?,?,?)", (user["organization_id"], str(form.get("name", "Other overhead")).strip(), number(form.get("monthly_cost")), integer(order["n"] if order else 1)))
    return redirect("/settings")


@app.get("/compliance", response_class=HTMLResponse)
def compliance_page(request: Request):
    user = require_user(request)
    rows = query_all("SELECT * FROM compliance_items WHERE organization_id=? ORDER BY expiration_date", (user["organization_id"],))
    items = []
    for row in rows:
        item = dict(row)
        item["status"], item["days"] = compliance_status(row["expiration_date"])
        items.append(item)
    bundle = get_bundle(user["organization_id"])
    return render(request, "compliance.html", {"items": items, "vehicles": bundle["vehicles"], "drivers": bundle["drivers"]})


@app.post("/compliance")
async def create_compliance_item(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    execute(
        """INSERT INTO compliance_items
        (organization_id,subject_type,subject_id,subject_name,document_type,expiration_date,notes)
        VALUES (?,?,?,?,?,?,?)""",
        (
            user["organization_id"], str(form.get("subject_type", "Company")), integer(form.get("subject_id")) or None,
            str(form.get("subject_name", user["organization_name"])).strip(), str(form.get("document_type", "Document")).strip(),
            str(form.get("expiration_date", "")) or None, str(form.get("notes", "")).strip(),
        ),
    )
    return redirect("/compliance")


@app.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(request: Request):
    user = require_user(request)
    rows = query_all("SELECT * FROM onboarding_applications WHERE organization_id=? ORDER BY created_at DESC", (user["organization_id"],))
    return render(request, "onboarding.html", {"applications": [dict(r) for r in rows]})


@app.post("/onboarding/invite")
async def onboarding_invite(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    token = new_onboarding_token()
    execute(
        "INSERT INTO onboarding_applications (organization_id,token,full_name,email,status) VALUES (?,?,?,?, 'Invited')",
        (user["organization_id"], token, str(form.get("full_name", "")).strip(), str(form.get("email", "")).strip()),
    )
    set_flash(request, f"Onboarding link created: /onboard/{token}")
    return redirect("/onboarding")


@app.get("/onboard/{token}", response_class=HTMLResponse)
def public_onboarding_page(request: Request, token: str):
    row = query_one(
        """SELECT a.*,o.name AS organization_name FROM onboarding_applications a
        JOIN organizations o ON o.id=a.organization_id WHERE a.token=?""", (token,),
    )
    if not row:
        raise HTTPException(404, "Onboarding link not found")
    return render(request, "public_onboarding.html", {"application": dict(row), "public_page": True})


@app.post("/onboard/{token}", response_class=HTMLResponse)
async def submit_onboarding(request: Request, token: str):
    row = query_one("SELECT * FROM onboarding_applications WHERE token=?", (token,))
    if not row:
        raise HTTPException(404, "Onboarding link not found")
    form = await verified_form(request)
    with db_session() as conn:
        conn.execute(
            """UPDATE onboarding_applications SET full_name=?,email=?,phone=?,license_number=?,
            license_state=?,medical_card_expiration=?,employment_history=?,emergency_contact=?,
            status='Submitted',submitted_at=? WHERE token=?""",
            (
                str(form.get("full_name", "")).strip(), str(form.get("email", "")).strip(), str(form.get("phone", "")).strip(),
                str(form.get("license_number", "")).strip(), str(form.get("license_state", "")).strip(),
                str(form.get("medical_card_expiration", "")) or None, str(form.get("employment_history", "")).strip(),
                str(form.get("emergency_contact", "")).strip(), utc_now_iso(), token,
            ),
        )
    updated = query_one(
        """SELECT a.*,o.name AS organization_name FROM onboarding_applications a
        JOIN organizations o ON o.id=a.organization_id WHERE a.token=?""", (token,),
    )
    return render(request, "public_onboarding.html", {"application": dict(updated), "submitted": True, "public_page": True})


DOCUMENT_TEMPLATES = [
    ("driver_handbook", "Driver handbook"),
    ("independent_contractor", "Independent-contractor template"),
    ("inspection_policy", "Vehicle inspection policy"),
    ("hours_of_service", "Hours-of-service policy"),
    ("load_securement", "Load-securement acknowledgement"),
    ("accident_response", "Accident-response procedure"),
    ("advance_authorization", "Advance and deduction authorization"),
    ("equipment_checkout", "Equipment checkout form"),
    ("detention_request", "Detention request"),
    ("payment_demand", "Past-due payment notice"),
]


def generate_document(document_type: str, company: str, effective_date: str, state: str, contact: str, notes: str) -> tuple[str, str]:
    labels = dict(DOCUMENT_TEMPLATES)
    title = labels.get(document_type, "Company document")
    intro = f"{company}\n{title.upper()}\nEffective date: {effective_date}\nPrimary state: {state}\nContact: {contact}\n"
    sections = {
        "driver_handbook": """PURPOSE\nThis handbook summarizes dispatch, safety, communication, equipment-care, documentation, payment, and incident-reporting expectations.\n\nCORE EXPECTATIONS\nDrivers must operate lawfully, protect cargo and equipment, communicate delays promptly, preserve shipping documents, and report accidents or damage immediately.\n\nPAY AND SETTLEMENTS\nPay follows the written compensation arrangement and completed-load documentation. Advances, reimbursements, non-load bonuses, and deductions must be identified separately.""",
        "independent_contractor": """SERVICES\nThe contractor may accept transportation work under separately confirmed terms and remains responsible for duties allocated by the signed master agreement.\n\nCOMPENSATION\nCompensation, expense responsibility, insurance, equipment, chargebacks, and termination terms must be completed in the signed agreement before work begins.""",
        "inspection_policy": """POLICY\nA pre-trip and post-trip inspection is required. Safety defects must be reported before continued operation. Inspection, repair, and out-of-service records must be retained as required.""",
        "hours_of_service": """POLICY\nNo dispatch instruction authorizes a driver to violate hours-of-service requirements. Drivers must keep records current and report when available hours are insufficient.""",
        "load_securement": """ACKNOWLEDGEMENT\nThe driver is responsible for inspecting cargo securement before movement and during transit at required intervals. Equipment must be appropriate, serviceable, and used according to applicable rules and shipper instructions.""",
        "accident_response": """IMMEDIATE STEPS\nProtect life, contact emergency services when needed, secure the scene, notify the company, avoid admitting fault, photograph conditions, collect witness information, and preserve all documents and electronic records.""",
        "advance_authorization": """AUTHORIZATION\nThe payee requests or acknowledges the listed advance, reimbursement, or deduction. Whether it reduces load pay must be marked explicitly on the settlement record and supported by the governing agreement.""",
        "equipment_checkout": """EQUIPMENT RECORD\nRecord the unit, trailer, keys, cards, permits, straps, chains, tarps, tools, and condition at issue and return. Damage or missing items must be documented with photographs.""",
        "detention_request": """SUBJECT: Detention request\nPlease process detention for the referenced shipment. Attach the rate confirmation, arrival/departure evidence, bill of lading, and calculation.\n\nLoad: [ENTER]\nArrival: [ENTER]\nDeparture: [ENTER]\nFree time: [ENTER]\nRequested amount: [ENTER]""",
        "payment_demand": """SUBJECT: Past-due transportation invoice\nOur records show the referenced invoice remains unpaid. Please confirm payment status, remittance date, or the specific documentation issue preventing payment.\n\nInvoice: [ENTER]\nLoad: [ENTER]\nBalance: [ENTER]\nDue date: [ENTER]""",
    }
    disclaimer = "\n\nREVIEW NOTICE\nThis operational template must be customized and reviewed by qualified legal, tax, insurance, safety, or compliance professionals before reliance."
    body = intro + "\n" + sections.get(document_type, notes or "[ENTER CONTENT]")
    if notes:
        body += f"\n\nCUSTOM NOTES\n{notes}"
    return title, (body + disclaimer).strip()


@app.get("/documents", response_class=HTMLResponse)
def documents_page(request: Request):
    user = require_user(request)
    rows = query_all("SELECT * FROM generated_documents WHERE organization_id=? ORDER BY created_at DESC", (user["organization_id"],))
    return render(request, "documents.html", {"documents": [dict(r) for r in rows], "document_types": DOCUMENT_TEMPLATES})


@app.post("/documents/generate")
async def create_document(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    doc_type = str(form.get("document_type", "driver_handbook"))
    title, body = generate_document(
        doc_type, str(form.get("company", user["organization_name"])), str(form.get("effective_date", date.today().isoformat())),
        str(form.get("state", "Tennessee")), str(form.get("contact", user["email"])), str(form.get("notes", "")).strip(),
    )
    doc_id = execute("INSERT INTO generated_documents (organization_id,title,document_type,body) VALUES (?,?,?,?)", (user["organization_id"], title, doc_type, body))
    return redirect(f"/documents/{doc_id}")


@app.get("/documents/{doc_id}", response_class=HTMLResponse)
def document_detail(request: Request, doc_id: int):
    user = require_user(request)
    row = query_one("SELECT * FROM generated_documents WHERE id=? AND organization_id=?", (doc_id, user["organization_id"]))
    if not row:
        raise HTTPException(404, "Document not found")
    return render(request, "document_detail.html", {"document": dict(row)})


@app.get("/documents/{doc_id}/docx")
def download_document_docx(request: Request, doc_id: int):
    user = require_user(request)
    row = query_one("SELECT * FROM generated_documents WHERE id=? AND organization_id=?", (doc_id, user["organization_id"]))
    if not row:
        raise HTTPException(404, "Document not found")
    doc = Document()
    doc.add_heading(row["title"], level=0)
    for block in row["body"].split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.isupper() and len(block) < 80:
            doc.add_heading(block.title(), level=1)
        else:
            doc.add_paragraph(block)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    filename = "_".join(row["title"].lower().split()) + ".docx"
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/receivables", response_class=HTMLResponse)
def receivables_page(request: Request):
    user = require_user(request)
    invoices = [invoice_aging(r) for r in query_all("SELECT * FROM invoices WHERE organization_id=? ORDER BY due_date", (user["organization_id"],))]
    claims = query_all(
        """SELECT c.*,l.load_number FROM detention_claims c LEFT JOIN loads l ON l.id=c.load_id
        WHERE c.organization_id=? ORDER BY c.created_at DESC""", (user["organization_id"],),
    )
    loads = query_all("SELECT id,load_number,broker FROM loads WHERE organization_id=? ORDER BY pickup_date DESC,id DESC", (user["organization_id"],))
    return render(request, "receivables.html", {"invoices": invoices, "claims": [dict(c) for c in claims], "loads": [dict(l) for l in loads]})


@app.post("/invoices")
async def create_invoice(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    invoice_date = str(form.get("invoice_date", date.today().isoformat()))
    due_date = str(form.get("due_date", (date.today() + timedelta(days=30)).isoformat()))
    execute(
        """INSERT INTO invoices
        (organization_id,invoice_number,customer,load_id,amount,invoice_date,due_date,status,notes)
        VALUES (?,?,?,?,?,?,?,'Unpaid',?)""",
        (user["organization_id"], str(form.get("invoice_number", "")).strip(), str(form.get("customer", "")).strip(), integer(form.get("load_id")) or None, number(form.get("amount")), invoice_date, due_date, str(form.get("notes", "")).strip()),
    )
    return redirect("/receivables")


@app.post("/invoices/{invoice_id}/paid")
async def mark_invoice_paid(request: Request, invoice_id: int):
    user = require_user(request)
    form = await verified_form(request)
    with db_session() as conn:
        conn.execute("UPDATE invoices SET status='Paid',paid_date=? WHERE id=? AND organization_id=?", (str(form.get("paid_date", date.today().isoformat())), invoice_id, user["organization_id"]))
    return redirect("/receivables")


@app.post("/detention")
async def create_detention_claim(request: Request):
    user = require_user(request)
    form = await verified_form(request)
    arrival_raw = str(form.get("arrival_at", ""))
    departure_raw = str(form.get("departure_at", ""))
    try:
        arrival = datetime.fromisoformat(arrival_raw)
        departure = datetime.fromisoformat(departure_raw)
    except ValueError as exc:
        raise HTTPException(400, "Enter valid arrival and departure times") from exc
    total_minutes = max(0.0, (departure - arrival).total_seconds() / 60)
    free_minutes = integer(form.get("free_minutes"), 120)
    rate = number(form.get("hourly_rate"), 75)
    amount = round(max(0.0, total_minutes - free_minutes) / 60 * rate, 2)
    execute(
        """INSERT INTO detention_claims
        (organization_id,load_id,broker,arrival_at,departure_at,free_minutes,hourly_rate,amount_claimed,status,notes)
        VALUES (?,?,?,?,?,?,?,?,'Draft',?)""",
        (user["organization_id"], integer(form.get("load_id")) or None, str(form.get("broker", "")).strip(), arrival_raw, departure_raw, free_minutes, rate, amount, str(form.get("notes", "")).strip()),
    )
    return redirect("/receivables")


@app.get("/detention/{claim_id}/draft", response_class=HTMLResponse)
def detention_draft(request: Request, claim_id: int):
    user = require_user(request)
    row = query_one(
        """SELECT c.*,l.load_number FROM detention_claims c LEFT JOIN loads l ON l.id=c.load_id
        WHERE c.id=? AND c.organization_id=?""", (claim_id, user["organization_id"]),
    )
    if not row:
        raise HTTPException(404, "Claim not found")
    total_minutes = (datetime.fromisoformat(row["departure_at"]) - datetime.fromisoformat(row["arrival_at"])).total_seconds() / 60
    billable = max(0.0, total_minutes - row["free_minutes"])
    draft = (
        f"Subject: Detention request - Load {row['load_number'] or 'N/A'}\n\n"
        f"Please process detention for load {row['load_number'] or 'N/A'}. The driver arrived at {row['arrival_at']} and departed at {row['departure_at']}. "
        f"After {row['free_minutes']} minutes of free time, {billable / 60:.2f} hours were billable at {money(row['hourly_rate'])} per hour. "
        f"The requested detention amount is {money(row['amount_claimed'])}.\n\n"
        "Please confirm receipt and advise the expected payment date. Attach the rate confirmation and supporting timestamps before sending."
    )
    return render(request, "detention_draft.html", {"claim": dict(row), "draft": draft})


@app.post("/api/quote")
async def api_quote(request: Request):
    user = require_user(request)
    payload = await request.json()
    bundle = get_bundle(user["organization_id"])
    driver = next((d for d in bundle["drivers"] if int(d["id"]) == integer(payload.get("driver_id"))), None)
    pickup = parse_date(payload.get("pickup_date"))
    if not driver or not pickup:
        return JSONResponse({"error": "Invalid driver or pickup date"}, status_code=400)
    result = calculate_quote(
        settings=bundle["settings"], driver=driver, pickup_date=pickup,
        loaded_miles=number(payload.get("loaded_miles")), deadhead_miles=number(payload.get("deadhead_miles")),
        trip_days=integer(payload.get("trip_days"), 1), fuel_price=number(payload.get("fuel_price")),
        tolls_misc=number(payload.get("tolls_misc")), other_direct_costs=number(payload.get("other_direct_costs")),
        quoted_revenue=optional_number(payload.get("quoted_revenue")), target_margin_pct=number(payload.get("target_margin_pct"), bundle["settings"]["target_margin_pct"]),
    )
    return result.to_dict()
