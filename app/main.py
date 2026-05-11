from dataclasses import asdict
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.db import (
    connect,
    delete_account,
    get_account,
    insert_account,
    list_accounts,
    update_account,
)
from app.projections import Account, project_total


class AccountIn(BaseModel):
    name: str
    balance_pence: int
    annual_rate_bp: int = 0
    monthly_allocation_pence: int = 0


DEFAULT_DB_PATH = Path("data/finance.db")
DEFAULT_HORIZONS_MONTHS = [0, 1, 3, 6, 12, 24, 60]
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Finance-Tracker")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


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


@app.post("/accounts", status_code=201)
def create_account(payload: AccountIn, db=Depends(get_db)) -> dict:
    account = Account(**payload.model_dump())
    account_id = insert_account(db, account)
    return asdict(get_account(db, account_id))


@app.put("/accounts/{account_id}")
def replace_account(account_id: int, payload: AccountIn, db=Depends(get_db)) -> dict:
    account = Account(**payload.model_dump())
    changed = update_account(db, account_id, account)
    if not changed:
        raise HTTPException(status_code=404, detail="account not found")
    return asdict(get_account(db, account_id))


@app.delete("/accounts/{account_id}", status_code=204)
def remove_account(account_id: int, db=Depends(get_db)) -> Response:
    deleted = delete_account(db, account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="account not found")
    return Response(status_code=204)


def _parse_horizons(value) -> list[int]:
    if value is None:
        horizons = list(DEFAULT_HORIZONS_MONTHS)
    else:
        horizons = [int(part) for part in value.split(",")]
    return horizons
