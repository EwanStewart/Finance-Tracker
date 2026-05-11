import sqlite3
from pathlib import Path
from typing import Iterable, Optional, Union

from app.projections import Account, IncomeSource

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance_pence INTEGER NOT NULL,
    annual_rate_bp INTEGER NOT NULL DEFAULT 0,
    monthly_allocation_pence INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS income_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    monthly_amount_pence INTEGER NOT NULL
);
"""


def connect(path: Union[str, Path]) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


INSERT_SQL = (
    "INSERT INTO accounts "
    "(name, balance_pence, annual_rate_bp, monthly_allocation_pence) "
    "VALUES (?, ?, ?, ?)"
)


def insert_account(conn: sqlite3.Connection, account: Account) -> int:
    cursor = conn.execute(
        INSERT_SQL,
        (
            account.name,
            account.balance_pence,
            account.annual_rate_bp,
            account.monthly_allocation_pence,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def list_accounts(conn: sqlite3.Connection) -> list[Account]:
    rows = conn.execute(
        "SELECT id, name, balance_pence, annual_rate_bp, monthly_allocation_pence "
        "FROM accounts ORDER BY id"
    ).fetchall()
    return [Account(**dict(row)) for row in rows]


def get_account(conn: sqlite3.Connection, account_id: int) -> Optional[Account]:
    row = conn.execute(
        "SELECT id, name, balance_pence, annual_rate_bp, monthly_allocation_pence "
        "FROM accounts WHERE id = ?",
        (account_id,),
    ).fetchone()
    return Account(**dict(row)) if row is not None else None


def update_account(conn: sqlite3.Connection, account_id: int, account: Account) -> bool:
    cursor = conn.execute(
        "UPDATE accounts SET name = ?, balance_pence = ?, annual_rate_bp = ?, "
        "monthly_allocation_pence = ? WHERE id = ?",
        (
            account.name,
            account.balance_pence,
            account.annual_rate_bp,
            account.monthly_allocation_pence,
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


def replace_accounts(conn: sqlite3.Connection, accounts: Iterable[Account]) -> None:
    rows = [
        (a.name, a.balance_pence, a.annual_rate_bp, a.monthly_allocation_pence)
        for a in accounts
    ]
    with conn:
        conn.execute("DELETE FROM accounts")
        conn.executemany(INSERT_SQL, rows)
