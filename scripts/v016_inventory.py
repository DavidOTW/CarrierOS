from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_SQL_CALLS = {"execute", "executemany", "executescript", "query_all", "query_one"}
MONEY_MARKERS = re.compile(r"\b(?:float|REAL)\b")
ROUTE_MARKER = re.compile(r"^@app\.(?:get|post|put|patch|delete)\(", re.MULTILINE)
TABLE_MARKER = re.compile(r"CREATE TABLE(?: IF NOT EXISTS)?\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)
PUBLIC_CLAIMS = re.compile(
    r"rate\s*con|settlement|automatic|extract|reconcil|real[- ]time|live\s+(?:gps|hos)|guarantee",
    re.I,
)


def _python_files(folder: str) -> list[Path]:
    return sorted((ROOT / folder).rglob("*.py"))


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _calls(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    found: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else None
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name not in RAW_SQL_CALLS:
            continue
        found.append(
            {
                "line": node.lineno,
                "call": name,
                "source": lines[node.lineno - 1].strip(),
            }
        )
    return sorted(found, key=lambda item: item["line"])


def _line_matches(path: Path, pattern: re.Pattern[str]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if pattern.search(line):
            matches.append({"line": line_number, "source": line.strip()})
    return matches


def build_inventory() -> dict[str, Any]:
    application_files = _python_files("app")
    raw_sql = {_relative(path): _calls(path) for path in application_files}
    raw_sql = {path: matches for path, matches in raw_sql.items() if matches}
    money_float = {
        _relative(path): _line_matches(path, MONEY_MARKERS) for path in application_files
    }
    money_float = {path: matches for path, matches in money_float.items() if matches}
    templates = sorted((ROOT / "app" / "templates").glob("*.html"))
    public_files = [
        ROOT / "app" / "templates" / "marketing.html",
        ROOT / "app" / "templates" / "demo.html",
        ROOT / "app" / "templates" / "seo_page.html",
        ROOT / "app" / "main.py",
        ROOT / "README.md",
    ]
    claims = {_relative(path): _line_matches(path, PUBLIC_CLAIMS) for path in public_files}
    claims = {path: matches for path, matches in claims.items() if matches}
    schema_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "app" / "db.py", ROOT / "app" / "v016_migration.py")
        if path.exists()
    )
    tests = _python_files("tests")
    test_definitions = sum(
        1
        for path in tests
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    )
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    return {
        "summary": {
            "route_decorators": len(ROUTE_MARKER.findall(main)),
            "templates": len(templates),
            "tables": len(set(TABLE_MARKER.findall(schema_source))),
            "migration_files": len(list((ROOT / "migrations").glob("*"))),
            "test_definitions": test_definitions,
            "raw_sql_calls": sum(len(items) for items in raw_sql.values()),
            "float_or_real_lines": sum(len(items) for items in money_float.values()),
        },
        "raw_sql": raw_sql,
        "money_float": money_float,
        "public_claim_candidates": claims,
        "raw_sql_counts": dict(sorted(Counter({k: len(v) for k, v in raw_sql.items()}).items())),
        "money_float_counts": dict(
            sorted(Counter({k: len(v) for k, v in money_float.items()}).items())
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory CarrierOS v0.16 review hotspots.")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    inventory = build_inventory()
    rendered = json.dumps(inventory, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
