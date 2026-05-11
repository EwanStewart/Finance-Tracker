from app.db import connect, insert_account, list_accounts, replace_accounts
from app.projections import Account


def test_list_accounts_is_empty_for_fresh_database():
    conn = connect(":memory:")

    result = list_accounts(conn)

    assert result == []


def test_inserted_account_is_returned_by_list():
    conn = connect(":memory:")
    account = Account(
        name="S&S ISA",
        balance_pence=17_615_25,
        annual_rate_bp=1110,
        monthly_allocation_pence=500_00,
    )

    insert_account(conn, account)

    assert list_accounts(conn) == [account]


def test_replace_accounts_wipes_existing_rows():
    conn = connect(":memory:")
    insert_account(conn, Account(name="Old", balance_pence=100_00))
    replacement = Account(name="New", balance_pence=200_00)

    replace_accounts(conn, [replacement])

    assert list_accounts(conn) == [replacement]
