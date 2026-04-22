from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch(base_url: str, path: str):
    req = Request(base_url.rstrip("/") + path, method="GET")
    with urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def size(value):
    return len(value) if isinstance(value, list) else -1


def probe(base_url: str, label: str, fail_on_error: bool) -> int:
    failures: list[str] = []

    try:
        health = fetch(base_url, "/health")
        latest = fetch(base_url, "/signals/latest?limit=200")
        long_top = fetch(base_url, "/signals/top?decision=LONG_SETUP&limit=20")
        short_top = fetch(base_url, "/signals/top?decision=SHORT_SETUP&limit=20")
        outcomes = fetch(base_url, "/outcomes/latest?limit=200")
        metrics = fetch(base_url, "/metrics/reports/latest?limit=200")
        live = fetch(base_url, "/metrics/live?horizon=4h")
        market = fetch(base_url, "/market/context")
        quality = fetch(base_url, "/quality/summary")
    except HTTPError as exc:
        failures.append(f"HTTPError {exc.code}: {exc.reason}")
    except URLError as exc:
        failures.append(f"URLError: {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"Unhandled: {exc}")

    if failures:
        print(f"{label}: FAIL base={base_url} errors={failures}")
        return 1 if fail_on_error else 0

    print(
        f"{label}: health={health.get('status')} latest={size(latest)} long={size(long_top)} "
        f"short={size(short_top)} outcomes={size(outcomes)} metrics={size(metrics)} "
        f"live={live.get('horizon', 'n/a')} market={market.get('status')} quality={quality.get('status')}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compact runtime probe for dashboard API endpoints")
    parser.add_argument("label", nargs="?", default="probe")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(sys.argv[1:])
    raise SystemExit(probe(base_url=args.base_url, label=args.label, fail_on_error=args.fail_on_error))
