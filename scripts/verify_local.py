"""Verify local server is up and endpoints work."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(BASE + path, timeout=5) as resp:
        return resp.status, resp.read()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    try:
        status, body = get("/api/health")
        data = json.loads(body)
        ok = status == 200 and data.get("status") == "ok"
        checks.append(("GET /api/health", ok, body.decode()))
    except Exception as exc:  # noqa: BLE001
        checks.append(("GET /api/health", False, str(exc)))

    try:
        status, body = get("/api/sample-data")
        data = json.loads(body)
        months = len(data.get("monthly_revenue", []))
        cats = len(data.get("by_category", []))
        ok = status == 200 and months == 12 and cats >= 3
        checks.append(("GET /api/sample-data", ok, f"months={months} categories={cats}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("GET /api/sample-data", False, str(exc)))

    try:
        status, body = get("/")
        text = body.decode("utf-8", "ignore")
        ok = status == 200 and "AI agent 数据分析" in text
        checks.append(("GET /", ok, f"status={status} bytes={len(body)}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("GET /", False, str(exc)))

    for path in ("/static/styles.css", "/static/app.js"):
        try:
            status, body = get(path)
            ok = status == 200 and len(body) > 100
            checks.append((f"GET {path}", ok, f"status={status} bytes={len(body)}"))
        except Exception as exc:  # noqa: BLE001
            checks.append((f"GET {path}", False, str(exc)))

    try:
        req = urllib.request.Request(
            BASE + "/api/analyze",
            data=json.dumps(
                {"question": "", "api_base": "x", "api_key": "y", "model": "z"}
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        checks.append(("POST /api/analyze (empty q)", False, "expected 422"))
    except urllib.error.HTTPError as exc:
        checks.append(("POST /api/analyze (empty q)", exc.code == 422, f"status={exc.code}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("POST /api/analyze (empty q)", False, str(exc)))

    all_ok = True
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  —  {detail}")
        all_ok = all_ok and ok

    print()
    print("RESULT:", "SUCCESS — 本地服务正常" if all_ok else "FAILED — 本地服务异常")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
