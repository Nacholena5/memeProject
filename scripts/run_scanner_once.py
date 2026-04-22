from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def run(base_url: str) -> int:
    req = Request(base_url.rstrip("/") + "/scanner/run", method="POST")
    try:
        with urlopen(req, timeout=40) as r:
            payload = json.loads(r.read().decode("utf-8"))
            print(json.dumps(payload, ensure_ascii=True, indent=2))
            return 0
    except HTTPError as exc:
        print(f"HTTPError {exc.code}: {exc.reason}")
        return 1
    except URLError as exc:
        print(f"URLError: {exc.reason}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run scanner once via /scanner/run")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    raise SystemExit(run(base_url=args.base_url))
