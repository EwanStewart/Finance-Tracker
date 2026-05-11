import openpyxl

from app.db import connect, list_accounts
from app.projections import Account
from app.seed import read_accounts_from_xlsx, seed_database


def _write_inputs_sheet(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inputs"
    ws["A1"] = "SAVINGS ACCOUNTS"
    ws["A2"] = "Account Name"
    ws["B2"] = "Balance (£)"
    ws["C2"] = "Annual Rate (%)"
    ws["D2"] = "Monthly Allocation (£)"
    ws["A3"] = "Test Savings"
    ws["B3"] = 1000.50
    ws["C3"] = 3.5
    ws["D3"] = 100.0
    ws["A4"] = "Other Savings"
    ws["B4"] = 200.0
    ws["C4"] = 5.0
    ws["D4"] = 0
    ws["A28"] = "TOTAL SAVINGS"
    ws["A30"] = "CREDIT CARDS"
    ws["A31"] = "Account Name"
    ws["B31"] = "Balance (£)"
    ws["A32"] = "Test Card"
    ws["B32"] = -250.0
    ws["A35"] = "TOTAL CC BALANCE"
    wb.save(path)


def test_read_accounts_parses_savings_and_credit_cards(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    _write_inputs_sheet(xlsx)

    accounts = read_accounts_from_xlsx(xlsx)

    assert accounts == [
        Account(
            name="Test Savings",
            balance_pence=100_050,
            annual_rate_bp=350,
            monthly_allocation_pence=10_000,
        ),
        Account(
            name="Other Savings",
            balance_pence=20_000,
            annual_rate_bp=500,
            monthly_allocation_pence=0,
        ),
        Account(
            name="Test Card",
            balance_pence=-25_000,
            annual_rate_bp=0,
            monthly_allocation_pence=0,
        ),
    ]


def test_seed_database_replaces_accounts(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    _write_inputs_sheet(xlsx)
    db_path = tmp_path / "test.db"

    count = seed_database(xlsx, db_path)

    assert count == 3
    conn = connect(db_path)
    assert len(list_accounts(conn)) == 3
