from dataclasses import asdict
from pathlib import Path
from typing import Generator, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.db import (
    connect,
    delete_account,
    delete_expense,
    delete_income_source,
    get_account,
    get_expense,
    get_income_source,
    insert_account,
    insert_expense,
    insert_income_source,
    list_accounts,
    list_expenses,
    list_income_sources,
    update_account,
    update_expense,
    update_income_source,
)
from app.projections import (
    Account,
    Expense,
    IncomeSource,
    monthly_summary,
    project_total,
)


class AccountIn(BaseModel):
    name: str
    balance_pence: int
    annual_rate_bp: int = 0
    monthly_allocation_pence: int = 0
    kind: Literal["savings", "credit_card"] = "savings"


class IncomeIn(BaseModel):
    name: str
    monthly_amount_pence: int


class ExpenseIn(BaseModel):
    name: str
    amount_pence: int
    cadence: Literal["monthly", "yearly"]


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


@app.get("/income")
def get_income(db=Depends(get_db)) -> list[dict]:
    return [asdict(source) for source in list_income_sources(db)]


@app.post("/income", status_code=201)
def create_income(payload: IncomeIn, db=Depends(get_db)) -> dict:
    source = IncomeSource(**payload.model_dump())
    source_id = insert_income_source(db, source)
    return asdict(get_income_source(db, source_id))


@app.put("/income/{source_id}")
def replace_income(source_id: int, payload: IncomeIn, db=Depends(get_db)) -> dict:
    source = IncomeSource(**payload.model_dump())
    changed = update_income_source(db, source_id, source)
    if not changed:
        raise HTTPException(status_code=404, detail="income source not found")
    return asdict(get_income_source(db, source_id))


@app.delete("/income/{source_id}", status_code=204)
def remove_income(source_id: int, db=Depends(get_db)) -> Response:
    deleted = delete_income_source(db, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="income source not found")
    return Response(status_code=204)


@app.get("/expenses")
def get_expenses(db=Depends(get_db)) -> list[dict]:
    return [asdict(expense) for expense in list_expenses(db)]


@app.post("/expenses", status_code=201)
def create_expense(payload: ExpenseIn, db=Depends(get_db)) -> dict:
    expense = Expense(**payload.model_dump())
    expense_id = insert_expense(db, expense)
    return asdict(get_expense(db, expense_id))


@app.put("/expenses/{expense_id}")
def replace_expense(expense_id: int, payload: ExpenseIn, db=Depends(get_db)) -> dict:
    expense = Expense(**payload.model_dump())
    changed = update_expense(db, expense_id, expense)
    if not changed:
        raise HTTPException(status_code=404, detail="expense not found")
    return asdict(get_expense(db, expense_id))


@app.delete("/expenses/{expense_id}", status_code=204)
def remove_expense(expense_id: int, db=Depends(get_db)) -> Response:
    deleted = delete_expense(db, expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="expense not found")
    return Response(status_code=204)


@app.get("/summary")
def get_summary(db=Depends(get_db)) -> dict:
    return monthly_summary(list_income_sources(db), list_expenses(db))


def _parse_horizons(value) -> list[int]:
    if value is None:
        horizons = list(DEFAULT_HORIZONS_MONTHS)
    else:
        horizons = [int(part) for part in value.split(",")]
    return horizons
