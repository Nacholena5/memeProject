from __future__ import annotations

from app.services.playbook_scanner_service import scanner_service


async def run_playbook_scan_cycle() -> dict:
    return await scanner_service.run_scan(trigger="scheduler")
