import asyncio

from app.jobs.run_scan_job import run_scan_cycle


async def main() -> None:
    top = await run_scan_cycle()
    for row in top[:10]:
        print(
            row["symbol"],
            row["decision"],
            round(row["long_score"], 2),
            round(row["short_score"], 2),
            round(row["confidence"], 2),
        )


if __name__ == "__main__":
    asyncio.run(main())
