from dataclasses import asdict
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, Query

from app.db import connect, list_accounts
from app.projections import project_total

DEFAULT_DB_PATH = Path("data/finance.db")
DEFAULT_HORIZONS_MONTHS = [0, 1, 3, 6, 12, 24, 60]

app = FastAPI(title="Finance-Tracker")


def get_db() -> Generator:
    conn = connect(DEFAULT_DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/accounts")
def get_accounts(db=Depends(get_db)) -> list[dict]:
    accounts = list_accounts(db)
    return [asdict(account) for account in accounts]


@app.get("/projections")
def get_projections(
    months: str = Query(default=None),
    db=Depends(get_db),
) -> list[dict]:
    horizons = _parse_horizons(months)
    accounts = list_accounts(db)
    points = [
        {"months": horizon, "total_pence": project_total(accounts, horizon)}
        for horizon in horizons
    ]
    return points


def _parse_horizons(value) -> list[int]:
    if value is None:
        horizons = list(DEFAULT_HORIZONS_MONTHS)
    else:
        horizons = [int(part) for part in value.split(",")]
    return horizons
