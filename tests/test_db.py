from dataclasses import replace

from app.db import (
    connect,
    delete_account,
    get_account,
    insert_account,
    list_accounts,
    replace_accounts,
    update_account,
)
from app.projections import Account


def test_list_accounts_is_empty_for_fresh_database():
    conn = connect(":memory:")

    result = list_accounts(conn)

    assert result == []


def test_inserted_account_is_returned_by_list_with_id():
    conn = connect(":memory:")
    account = Account(
        name="S&S ISA",
        balance_pence=17_615_25,
        annual_rate_bp=1110,
        monthly_allocation_pence=500_00,
    )

    account_id = insert_account(conn, account)

    assert list_accounts(conn) == [replace(account, id=account_id)]


def test_replace_accounts_wipes_existing_rows():
    conn = connect(":memory:")
    insert_account(conn, Account(name="Old", balance_pence=100_00))
    replacement = Account(name="New", balance_pence=200_00)

    replace_accounts(conn, [replacement])

    rows = list_accounts(conn)
    assert len(rows) == 1
    assert rows[0].name == "New"
    assert rows[0].balance_pence == 200_00


def test_get_account_returns_none_when_missing():
    conn = connect(":memory:")

    assert get_account(conn, 99) is None


def test_get_account_returns_account_by_id():
    conn = connect(":memory:")
    account_id = insert_account(conn, Account(name="Cash ISA", balance_pence=100_00))

    result = get_account(conn, account_id)

    assert result is not None
    assert result.id == account_id
    assert result.name == "Cash ISA"


def test_update_account_modifies_existing_row():
    conn = connect(":memory:")
    account_id = insert_account(conn, Account(name="Old", balance_pence=100_00))

    changed = update_account(
        conn, account_id, Account(name="Renamed", balance_pence=250_00)
    )

    assert changed is True
    refreshed = get_account(conn, account_id)
    assert refreshed.name == "Renamed"
    assert refreshed.balance_pence == 250_00


def test_update_account_returns_false_when_missing():
    conn = connect(":memory:")

    changed = update_account(conn, 99, Account(name="X", balance_pence=0))

    assert changed is False


def test_delete_account_removes_row():
    conn = connect(":memory:")
    account_id = insert_account(conn, Account(name="Gone", balance_pence=0))

    deleted = delete_account(conn, account_id)

    assert deleted is True
    assert get_account(conn, account_id) is None


def test_delete_account_returns_false_when_missing():
    conn = connect(":memory:")

    assert delete_account(conn, 99) is False
