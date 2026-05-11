import sqlite3
from pathlib import Path
from typing import Iterable, Optional, Union

from app.projections import Account

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance_pence INTEGER NOT NULL,
    annual_rate_bp INTEGER NOT NULL DEFAULT 0,
    monthly_allocation_pence INTEGER NOT NULL DEFAULT 0
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


def replace_accounts(conn: sqlite3.Connection, accounts: Iterable[Account]) -> None:
    rows = [
        (a.name, a.balance_pence, a.annual_rate_bp, a.monthly_allocation_pence)
        for a in accounts
    ]
    with conn:
        conn.execute("DELETE FROM accounts")
        conn.executemany(INSERT_SQL, rows)
