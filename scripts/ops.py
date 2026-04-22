from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")


def _run(cmd: list[str], env: dict[str, str] | None = None) -> int:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    process = subprocess.run(cmd, cwd=ROOT, env=merged_env)
    return process.returncode


def serve_sqlite(host: str, port: int, reload_mode: bool) -> int:
    cmd = [PYTHON, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)]
    if reload_mode:
        cmd.append("--reload")
    return _run(cmd, env={"DATABASE_URL": "sqlite:///./meme_research.db"})


def serve_postgres(host: str, port: int, reload_mode: bool) -> int:
    cmd = [PYTHON, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)]
    if reload_mode:
        cmd.append("--reload")
    return _run(cmd)


def scenario(mode: str) -> int:
    return _run([PYTHON, "scripts/set_qa_scenario.py", mode])


def seed_demo() -> int:
    return _run([PYTHON, "scripts/seed_demo_data.py"])


def probe(base_url: str) -> int:
    return _run([PYTHON, "scripts/probe_api.py", "--base-url", base_url, "--fail-on-error"])


def e2e(base_url: str, smoke_only: bool) -> int:
    env = {"E2E_BASE_URL": base_url}
    test_target = "tests/e2e/test_dashboard_e2e.py"
    if smoke_only:
        test_target = "tests/e2e/test_dashboard_e2e.py::test_dashboard_loads_shell"
    return _run([PYTHON, "-m", "pytest", test_target, "-q"], env=env)


def capture(base_url: str) -> int:
    return _run([PYTHON, "scripts/capture_dashboard_evidence.py", "--base-url", base_url])


def scanner_run(base_url: str) -> int:
    return _run([PYTHON, "scripts/run_scanner_once.py", "--base-url", base_url])


def backup(name: str) -> int:
    cmd = [PYTHON, "scripts/backup_db.py"]
    if name:
        cmd.extend(["--name", name])
    return _run(cmd)


def restore(backup_file: str) -> int:
    return _run([PYTHON, "scripts/restore_db.py", backup_file])


def reset_demo() -> int:
    return _run([PYTHON, "scripts/reset_demo_state.py"])


def demo_ready(base_url: str) -> int:
    steps = [
        ("scenario_full", scenario("full")),
        ("probe", probe(base_url)),
        ("capture", capture(base_url)),
    ]
    failed = [name for name, code in steps if code != 0]
    if failed:
        print(f"demo-ready failed at: {', '.join(failed)}")
        return 1
    print("demo-ready completed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operational helper CLI for memeproject release workflows")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_sqlite_p = sub.add_parser("serve-sqlite", help="Run API using local SQLite fallback")
    serve_sqlite_p.add_argument("--host", default="127.0.0.1")
    serve_sqlite_p.add_argument("--port", type=int, default=8000)
    serve_sqlite_p.add_argument("--reload", action="store_true")

    serve_pg_p = sub.add_parser("serve-postgres", help="Run API using DATABASE_URL from environment/.env")
    serve_pg_p.add_argument("--host", default="127.0.0.1")
    serve_pg_p.add_argument("--port", type=int, default=8000)
    serve_pg_p.add_argument("--reload", action="store_true")

    scenario_p = sub.add_parser("scenario", help="Apply QA scenario dataset")
    scenario_p.add_argument("mode", choices=["full", "partial", "empty"])

    sub.add_parser("seed-demo", help="Seed demo data if DB is empty")

    probe_p = sub.add_parser("probe", help="Probe API endpoints and print a compact health report")
    probe_p.add_argument("--base-url", default="http://127.0.0.1:8000")

    e2e_p = sub.add_parser("e2e", help="Run Playwright E2E tests")
    e2e_p.add_argument("--base-url", default="http://127.0.0.1:8000")
    e2e_p.add_argument("--smoke", action="store_true")

    capture_p = sub.add_parser("capture", help="Capture dashboard screenshot + runtime report")
    capture_p.add_argument("--base-url", default="http://127.0.0.1:8000")

    scanner_run_p = sub.add_parser("scanner-run", help="Run playbook scanner once via HTTP endpoint")
    scanner_run_p.add_argument("--base-url", default="http://127.0.0.1:8000")

    demo_p = sub.add_parser("demo-ready", help="Reset dataset and regenerate demo evidence")
    demo_p.add_argument("--base-url", default="http://127.0.0.1:8000")

    backup_p = sub.add_parser("backup-db", help="Create timestamped SQLite backup")
    backup_p.add_argument("--name", default="")

    restore_p = sub.add_parser("restore-db", help="Restore SQLite DB from backup file")
    restore_p.add_argument("backup_file")

    sub.add_parser("reset-demo", help="Restore full demo dataset")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "serve-sqlite":
        return serve_sqlite(host=args.host, port=args.port, reload_mode=args.reload)
    if args.command == "serve-postgres":
        return serve_postgres(host=args.host, port=args.port, reload_mode=args.reload)
    if args.command == "scenario":
        return scenario(args.mode)
    if args.command == "seed-demo":
        return seed_demo()
    if args.command == "probe":
        return probe(args.base_url)
    if args.command == "e2e":
        return e2e(base_url=args.base_url, smoke_only=args.smoke)
    if args.command == "capture":
        return capture(args.base_url)
    if args.command == "scanner-run":
        return scanner_run(args.base_url)
    if args.command == "demo-ready":
        return demo_ready(args.base_url)
    if args.command == "backup-db":
        return backup(args.name)
    if args.command == "restore-db":
        return restore(args.backup_file)
    if args.command == "reset-demo":
        return reset_demo()

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
