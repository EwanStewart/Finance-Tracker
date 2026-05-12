import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Union

from app.projections import Account, Expense, IncomeSource, Snapshot

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance_pence INTEGER NOT NULL,
    annual_rate_bp INTEGER NOT NULL DEFAULT 0,
    monthly_allocation_pence INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL DEFAULT 'savings' CHECK (kind IN ('savings', 'credit_card'))
);

CREATE TABLE IF NOT EXISTS income_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    monthly_amount_pence INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount_pence INTEGER NOT NULL,
    cadence TEXT NOT NULL CHECK (cadence IN ('monthly', 'yearly'))
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taken_at TEXT NOT NULL,
    trigger TEXT NOT NULL DEFAULT 'manual' CHECK (trigger IN ('manual', 'write')),
    label TEXT,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_taken_at ON snapshots(taken_at);
"""


def connect(path: Union[str, Path]) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()
    ]
    if "kind" not in columns:
        conn.execute(
            "ALTER TABLE accounts ADD COLUMN kind TEXT NOT NULL DEFAULT 'savings'"
        )
        conn.commit()


INSERT_SQL = (
    "INSERT INTO accounts "
    "(name, balance_pence, annual_rate_bp, monthly_allocation_pence, kind) "
    "VALUES (?, ?, ?, ?, ?)"
)

_ACCOUNT_COLUMNS = (
    "id, name, balance_pence, annual_rate_bp, monthly_allocation_pence, kind"
)


def insert_account(conn: sqlite3.Connection, account: Account) -> int:
    cursor = conn.execute(
        INSERT_SQL,
        (
            account.name,
            account.balance_pence,
            account.annual_rate_bp,
            account.monthly_allocation_pence,
            account.kind,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def list_accounts(conn: sqlite3.Connection) -> list[Account]:
    rows = conn.execute(
        f"SELECT {_ACCOUNT_COLUMNS} FROM accounts ORDER BY id"
    ).fetchall()
    return [Account(**dict(row)) for row in rows]


def get_account(conn: sqlite3.Connection, account_id: int) -> Optional[Account]:
    row = conn.execute(
        f"SELECT {_ACCOUNT_COLUMNS} FROM accounts WHERE id = ?",
        (account_id,),
    ).fetchone()
    return Account(**dict(row)) if row is not None else None


def update_account(conn: sqlite3.Connection, account_id: int, account: Account) -> bool:
    cursor = conn.execute(
        "UPDATE accounts SET name = ?, balance_pence = ?, annual_rate_bp = ?, "
        "monthly_allocation_pence = ?, kind = ? WHERE id = ?",
        (
            account.name,
            account.balance_pence,
            account.annual_rate_bp,
            account.monthly_allocation_pence,
            account.kind,
            account_id,
        ),
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_account(conn: sqlite3.Connection, account_id: int) -> bool:
    cursor = conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    return cursor.rowcount > 0


INCOME_INSERT_SQL = (
    "INSERT INTO income_sources (name, monthly_amount_pence) VALUES (?, ?)"
)


def insert_income_source(conn: sqlite3.Connection, source: IncomeSource) -> int:
    cursor = conn.execute(INCOME_INSERT_SQL, (source.name, source.monthly_amount_pence))
    conn.commit()
    return cursor.lastrowid


def list_income_sources(conn: sqlite3.Connection) -> list[IncomeSource]:
    rows = conn.execute(
        "SELECT id, name, monthly_amount_pence FROM income_sources ORDER BY id"
    ).fetchall()
    return [IncomeSource(**dict(row)) for row in rows]


def get_income_source(
    conn: sqlite3.Connection, source_id: int
) -> Optional[IncomeSource]:
    row = conn.execute(
        "SELECT id, name, monthly_amount_pence FROM income_sources WHERE id = ?",
        (source_id,),
    ).fetchone()
    return IncomeSource(**dict(row)) if row is not None else None


def update_income_source(
    conn: sqlite3.Connection, source_id: int, source: IncomeSource
) -> bool:
    cursor = conn.execute(
        "UPDATE income_sources SET name = ?, monthly_amount_pence = ? WHERE id = ?",
        (source.name, source.monthly_amount_pence, source_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_income_source(conn: sqlite3.Connection, source_id: int) -> bool:
    cursor = conn.execute("DELETE FROM income_sources WHERE id = ?", (source_id,))
    conn.commit()
    return cursor.rowcount > 0


EXPENSE_INSERT_SQL = (
    "INSERT INTO expenses (name, amount_pence, cadence) VALUES (?, ?, ?)"
)


def insert_expense(conn: sqlite3.Connection, expense: Expense) -> int:
    cursor = conn.execute(
        EXPENSE_INSERT_SQL, (expense.name, expense.amount_pence, expense.cadence)
    )
    conn.commit()
    return cursor.lastrowid


def list_expenses(conn: sqlite3.Connection) -> list[Expense]:
    rows = conn.execute(
        "SELECT id, name, amount_pence, cadence FROM expenses ORDER BY id"
    ).fetchall()
    return [Expense(**dict(row)) for row in rows]


def get_expense(conn: sqlite3.Connection, expense_id: int) -> Optional[Expense]:
    row = conn.execute(
        "SELECT id, name, amount_pence, cadence FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    return Expense(**dict(row)) if row is not None else None


def update_expense(conn: sqlite3.Connection, expense_id: int, expense: Expense) -> bool:
    cursor = conn.execute(
        "UPDATE expenses SET name = ?, amount_pence = ?, cadence = ? WHERE id = ?",
        (expense.name, expense.amount_pence, expense.cadence, expense_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_expense(conn: sqlite3.Connection, expense_id: int) -> bool:
    cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    return cursor.rowcount > 0


def replace_accounts(conn: sqlite3.Connection, accounts: Iterable[Account]) -> None:
    rows = [
        (a.name, a.balance_pence, a.annual_rate_bp, a.monthly_allocation_pence, a.kind)
        for a in accounts
    ]
    with conn:
        conn.execute("DELETE FROM accounts")
        conn.executemany(INSERT_SQL, rows)


_SNAPSHOT_COLUMNS = "id, taken_at, trigger, label, payload"


def _row_to_snapshot(row: sqlite3.Row) -> Snapshot:
    return Snapshot(
        id=row["id"],
        taken_at=row["taken_at"],
        trigger=row["trigger"],
        label=row["label"],
        payload=json.loads(row["payload"]),
    )


def insert_snapshot(conn: sqlite3.Connection, snapshot: Snapshot) -> int:
    cursor = conn.execute(
        "INSERT INTO snapshots (taken_at, trigger, label, payload) "
        "VALUES (?, ?, ?, ?)",
        (
            snapshot.taken_at,
            snapshot.trigger,
            snapshot.label,
            json.dumps(snapshot.payload),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def list_snapshots(conn: sqlite3.Connection) -> list[Snapshot]:
    rows = conn.execute(
        f"SELECT {_SNAPSHOT_COLUMNS} FROM snapshots ORDER BY taken_at, id"
    ).fetchall()
    return [_row_to_snapshot(row) for row in rows]


def latest_snapshot(conn: sqlite3.Connection) -> Optional[Snapshot]:
    row = conn.execute(
        f"SELECT {_SNAPSHOT_COLUMNS} FROM snapshots "
        "ORDER BY taken_at DESC, id DESC LIMIT 1"
    ).fetchone()
    return _row_to_snapshot(row) if row is not None else None


def delete_snapshot(conn: sqlite3.Connection, snapshot_id: int) -> bool:
    cursor = conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
    conn.commit()
    return cursor.rowcount > 0


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


def build_snapshot_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    accounts = list_accounts(conn)
    income = list_income_sources(conn)
    expenses = list_expenses(conn)
    total_pence = sum(account.balance_pence for account in accounts)
    return {
        "accounts": [asdict(account) for account in accounts],
        "income": [asdict(source) for source in income],
        "expenses": [asdict(expense) for expense in expenses],
        "total_pence": total_pence,
    }


def capture_snapshot(
    conn: sqlite3.Connection,
    trigger: str = "manual",
    label: Optional[str] = None,
    now_fn: Callable[[], str] = _utcnow_iso,
    debounce_seconds: int = 60,
) -> Snapshot:
    taken_at = now_fn()
    payload = build_snapshot_payload(conn)
    previous = latest_snapshot(conn)
    should_replace = (
        trigger == "write"
        and previous is not None
        and previous.trigger == "write"
        and (_parse_iso(taken_at) - _parse_iso(previous.taken_at)).total_seconds()
        < debounce_seconds
    )
    if should_replace:
        conn.execute(
            "UPDATE snapshots SET taken_at = ?, trigger = ?, label = ?, payload = ? "
            "WHERE id = ?",
            (taken_at, trigger, label, json.dumps(payload), previous.id),
        )
        conn.commit()
        snapshot_id = previous.id
    else:
        snapshot_id = insert_snapshot(
            conn,
            Snapshot(taken_at=taken_at, payload=payload, trigger=trigger, label=label),
        )
    result = Snapshot(
        id=snapshot_id,
        taken_at=taken_at,
        payload=payload,
        trigger=trigger,
        label=label,
    )
    return result
