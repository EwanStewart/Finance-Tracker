import argparse
from pathlib import Path
from typing import Optional, Union

import openpyxl

from app.db import connect, replace_accounts
from app.projections import Account


def _to_pence(value, multiplier=100):
    pence = round(float(value or 0) * multiplier)
    return pence


def _find_header_row(ws, text):
    result = None
    for row in range(1, 100):
        value = ws.cell(row=row, column=1).value
        if value and str(value).upper() == text.upper():
            result = row
            break
    return result


def _read_savings(ws) -> list[Account]:
    accounts: list[Account] = []
    for row in range(3, 28):
        name = ws.cell(row=row, column=1).value
        if not name:
            break
        accounts.append(
            Account(
                name=str(name),
                balance_pence=_to_pence(ws.cell(row=row, column=2).value),
                annual_rate_bp=_to_pence(ws.cell(row=row, column=3).value),
                monthly_allocation_pence=_to_pence(ws.cell(row=row, column=4).value),
            )
        )
    return accounts


def _read_credit_cards(ws) -> list[Account]:
    accounts: list[Account] = []
    start = _find_header_row(ws, "CREDIT CARDS")
    if start is not None:
        for row in range(start + 2, start + 30):
            name = ws.cell(row=row, column=1).value
            if not name or "TOTAL" in str(name).upper():
                break
            accounts.append(
                Account(
                    name=str(name),
                    balance_pence=_to_pence(ws.cell(row=row, column=2).value),
                )
            )
    return accounts


def read_accounts_from_xlsx(path: Union[str, Path]) -> list[Account]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    worksheet = workbook["Inputs"]
    accounts = _read_savings(worksheet) + _read_credit_cards(worksheet)
    return accounts


def seed_database(xlsx_path: Union[str, Path], db_path: Union[str, Path]) -> int:
    accounts = read_accounts_from_xlsx(xlsx_path)
    conn = connect(db_path)
    replace_accounts(conn, accounts)
    return len(accounts)


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Seed the database from a Finances.xlsx file"
    )
    parser.add_argument(
        "xlsx",
        type=Path,
        nargs="?",
        default=Path("data/Finances.xlsx"),
        help="Path to xlsx (default: data/Finances.xlsx)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/finance.db"),
        help="Path to SQLite database (default: data/finance.db)",
    )
    args = parser.parse_args(argv)
    args.db.parent.mkdir(parents=True, exist_ok=True)
    count = seed_database(args.xlsx, args.db)
    print(f"Seeded {count} accounts from {args.xlsx} into {args.db}")


if __name__ == "__main__":
    main()
