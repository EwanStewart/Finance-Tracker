from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Generator, Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AfterValidator, BaseModel, model_validator

from app.db import (
    capture_snapshot,
    connect,
    delete_account,
    delete_expense,
    delete_income_source,
    delete_snapshot,
    get_account,
    get_expense,
    get_fund_price,
    get_income_source,
    insert_account,
    insert_expense,
    insert_income_source,
    list_accounts,
    list_expenses,
    list_income_sources,
    list_snapshots,
    save_fund_price,
    update_account,
    update_expense,
    update_income_source,
)
from app.fund import FACTSHEET_URL, FUND_ISIN, FundPriceError, fetch_price
from app.projections import (
    Account,
    Expense,
    IncomeSource,
    monthly_summary,
    project_total,
    unallocated_surplus,
)


def _require_name(value: str) -> str:
    """Reject a blank name before it reaches the database."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("name cannot be blank")
    return cleaned


Name = Annotated[str, AfterValidator(_require_name)]


class AccountIn(BaseModel):
    name: Name
    balance_pence: int
    annual_rate_bp: int = 0
    monthly_allocation_pence: int = 0
    kind: Literal["savings", "credit_card"] = "savings"
    bank: Literal["Moneybox", "RBS"] = "RBS"

    @model_validator(mode="after")
    def card_balance_is_debt(self) -> "AccountIn":
        """A credit card balance is money owed, so it is always held negative."""
        if self.kind == "credit_card" and self.balance_pence > 0:
            self.balance_pence = -self.balance_pence
        return self


class IncomeIn(BaseModel):
    name: Name
    monthly_amount_pence: int


class ExpenseIn(BaseModel):
    name: Name
    amount_pence: int
    cadence: Literal["monthly", "yearly"]
    renewal_date: str | None = None


class SnapshotIn(BaseModel):
    label: str | None = None


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "finance.db"
DEFAULT_HORIZONS_MONTHS = [0, 1, 3, 6, 12, 24, 60]
STATIC_DIR = Path(__file__).parent / "static"

# Moneybox leads the list because it holds the ISAs and the reward savings.
BANKS = [
    {"name": "Moneybox", "logo": "/logos/moneybox.png"},
    {"name": "RBS", "logo": "/logos/rbs.svg"},
]

app = FastAPI(title="Finance-Tracker")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/logos", StaticFiles(directory=STATIC_DIR / "logos"), name="logos")


def get_db() -> Generator:
    conn = connect(DEFAULT_DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/banks")
def get_banks() -> list[dict]:
    return BANKS


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
    surplus = _monthly_surplus(db, accounts)
    points = [
        {
            "months": horizon,
            "total_pence": project_total(accounts, horizon, surplus),
        }
        for horizon in horizons
    ]
    return points


@app.post("/accounts", status_code=201)
def create_account(payload: AccountIn, db=Depends(get_db)) -> dict:
    account = Account(**payload.model_dump())
    account_id = insert_account(db, account)
    capture_snapshot(db, trigger="Write")
    return asdict(get_account(db, account_id))


@app.put("/accounts/{account_id}")
def replace_account(account_id: int, payload: AccountIn, db=Depends(get_db)) -> dict:
    account = Account(**payload.model_dump())
    changed = update_account(db, account_id, account)
    if not changed:
        raise HTTPException(status_code=404, detail="account not found")
    capture_snapshot(db, trigger="Write")
    return asdict(get_account(db, account_id))


@app.delete("/accounts/{account_id}", status_code=204)
def remove_account(account_id: int, db=Depends(get_db)) -> Response:
    deleted = delete_account(db, account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="account not found")
    capture_snapshot(db, trigger="Write")
    return Response(status_code=204)


@app.get("/income")
def get_income(db=Depends(get_db)) -> list[dict]:
    return [asdict(source) for source in list_income_sources(db)]


@app.post("/income", status_code=201)
def create_income(payload: IncomeIn, db=Depends(get_db)) -> dict:
    source = IncomeSource(**payload.model_dump())
    source_id = insert_income_source(db, source)
    capture_snapshot(db, trigger="Write")
    return asdict(get_income_source(db, source_id))


@app.put("/income/{source_id}")
def replace_income(source_id: int, payload: IncomeIn, db=Depends(get_db)) -> dict:
    source = IncomeSource(**payload.model_dump())
    changed = update_income_source(db, source_id, source)
    if not changed:
        raise HTTPException(status_code=404, detail="income source not found")
    capture_snapshot(db, trigger="Write")
    return asdict(get_income_source(db, source_id))


@app.delete("/income/{source_id}", status_code=204)
def remove_income(source_id: int, db=Depends(get_db)) -> Response:
    deleted = delete_income_source(db, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="income source not found")
    capture_snapshot(db, trigger="Write")
    return Response(status_code=204)


@app.get("/expenses")
def get_expenses(db=Depends(get_db)) -> list[dict]:
    return [asdict(expense) for expense in list_expenses(db)]


@app.post("/expenses", status_code=201)
def create_expense(payload: ExpenseIn, db=Depends(get_db)) -> dict:
    expense = Expense(**payload.model_dump())
    expense_id = insert_expense(db, expense)
    capture_snapshot(db, trigger="Write")
    return asdict(get_expense(db, expense_id))


@app.put("/expenses/{expense_id}")
def replace_expense(expense_id: int, payload: ExpenseIn, db=Depends(get_db)) -> dict:
    expense = Expense(**payload.model_dump())
    changed = update_expense(db, expense_id, expense)
    if not changed:
        raise HTTPException(status_code=404, detail="expense not found")
    capture_snapshot(db, trigger="Write")
    return asdict(get_expense(db, expense_id))


@app.delete("/expenses/{expense_id}", status_code=204)
def remove_expense(expense_id: int, db=Depends(get_db)) -> Response:
    deleted = delete_expense(db, expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="expense not found")
    capture_snapshot(db, trigger="Write")
    return Response(status_code=204)


def _today_in_london() -> str:
    return datetime.now(ZoneInfo("Europe/London")).date().isoformat()


def _fund_price_payload(row: dict[str, Any], stale: bool) -> dict:
    payload = dict(row)
    payload["stale"] = stale
    payload["source_url"] = FACTSHEET_URL
    return payload


def _refresh_fund_price(db, cached: Optional[dict[str, Any]], today: str) -> dict:
    try:
        price = fetch_price()
    except (FundPriceError, OSError) as error:
        if cached is None:
            raise HTTPException(
                status_code=503, detail="fund price unavailable"
            ) from error
        result = _fund_price_payload(cached, stale=True)
    else:
        save_fund_price(db, price, today)
        result = _fund_price_payload(get_fund_price(db, FUND_ISIN), stale=False)
    return result


@app.get("/fund-price")
def get_fund(db=Depends(get_db)) -> dict:
    cached = get_fund_price(db, FUND_ISIN)
    today = _today_in_london()
    if cached is not None and cached["fetched_on"] == today:
        result = _fund_price_payload(cached, stale=False)
    else:
        result = _refresh_fund_price(db, cached, today)
    return result


def _monthly_surplus(db, accounts) -> int:
    summary = monthly_summary(list_income_sources(db), list_expenses(db))
    return unallocated_surplus(accounts, summary["available_to_save_pence"])


@app.get("/summary")
def get_summary(db=Depends(get_db)) -> dict:
    summary = monthly_summary(list_income_sources(db), list_expenses(db))
    summary["unallocated_surplus_pence"] = unallocated_surplus(
        list_accounts(db), summary["available_to_save_pence"]
    )
    return summary


def _snapshot_to_dict(snapshot) -> dict:
    return {
        "id": snapshot.id,
        "taken_at": snapshot.taken_at,
        "trigger": snapshot.trigger,
        "label": snapshot.label,
        "payload": snapshot.payload,
    }


@app.get("/snapshots")
def get_snapshots(db=Depends(get_db)) -> list[dict]:
    return [_snapshot_to_dict(snapshot) for snapshot in list_snapshots(db)]


@app.post("/snapshots", status_code=201)
def create_snapshot(payload: SnapshotIn, db=Depends(get_db)) -> dict:
    snapshot = capture_snapshot(db, trigger="Manual", label=payload.label)
    return _snapshot_to_dict(snapshot)


@app.delete("/snapshots/{snapshot_id}", status_code=204)
def remove_snapshot(snapshot_id: int, db=Depends(get_db)) -> Response:
    deleted = delete_snapshot(db, snapshot_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="snapshot not found")
    return Response(status_code=204)


def _parse_horizons(value: Optional[str]) -> list[int]:
    if value is None:
        horizons = list(DEFAULT_HORIZONS_MONTHS)
    else:
        try:
            horizons = [int(part) for part in value.split(",")]
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail="months must be whole numbers"
            ) from error
        if any(horizon < 0 for horizon in horizons):
            raise HTTPException(status_code=422, detail="months cannot be negative")
    return horizons
