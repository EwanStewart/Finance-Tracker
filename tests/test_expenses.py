from dataclasses import replace

import pytest

from app.db import (
    connect,
    delete_expense,
    get_expense,
    insert_expense,
    list_expenses,
    update_expense,
)
from app.projections import Expense


def test_list_expenses_is_empty_for_fresh_database():
    conn = connect(":memory:")

    assert list_expenses(conn) == []


def test_inserted_expense_is_returned_with_id():
    conn = connect(":memory:")
    expense = Expense(name="Rent", amount_pence=200_00, cadence="monthly")

    expense_id = insert_expense(conn, expense)

    assert list_expenses(conn) == [replace(expense, id=expense_id)]


def test_insert_rejects_invalid_cadence():
    conn = connect(":memory:")

    with pytest.raises(Exception):
        insert_expense(conn, Expense(name="X", amount_pence=10, cadence="weekly"))


def test_get_expense_returns_none_when_missing():
    conn = connect(":memory:")

    assert get_expense(conn, 99) is None


def test_update_expense_modifies_existing_row():
    conn = connect(":memory:")
    expense_id = insert_expense(
        conn, Expense(name="Rent", amount_pence=200_00, cadence="monthly")
    )

    changed = update_expense(
        conn,
        expense_id,
        Expense(name="Rent", amount_pence=250_00, cadence="monthly"),
    )

    assert changed is True
    assert get_expense(conn, expense_id).amount_pence == 250_00


def test_update_expense_returns_false_when_missing():
    conn = connect(":memory:")

    changed = update_expense(
        conn, 99, Expense(name="X", amount_pence=0, cadence="monthly")
    )

    assert changed is False


def test_delete_expense_removes_row():
    conn = connect(":memory:")
    expense_id = insert_expense(
        conn, Expense(name="Gone", amount_pence=0, cadence="yearly")
    )

    deleted = delete_expense(conn, expense_id)

    assert deleted is True
    assert get_expense(conn, expense_id) is None


def test_delete_expense_returns_false_when_missing():
    conn = connect(":memory:")

    assert delete_expense(conn, 99) is False


def test_renewal_date_persists_for_yearly_expense():
    conn = connect(":memory:")
    expense = Expense(
        name="Car Insurance",
        amount_pence=700_00,
        cadence="yearly",
        renewal_date="2026-06-18",
    )

    expense_id = insert_expense(conn, expense)

    assert get_expense(conn, expense_id).renewal_date == "2026-06-18"


def test_renewal_date_defaults_to_none():
    conn = connect(":memory:")
    expense_id = insert_expense(
        conn, Expense(name="Rent", amount_pence=200_00, cadence="monthly")
    )

    assert get_expense(conn, expense_id).renewal_date is None


def test_update_expense_changes_renewal_date():
    conn = connect(":memory:")
    expense_id = insert_expense(
        conn,
        Expense(
            name="Car Insurance",
            amount_pence=700_00,
            cadence="yearly",
            renewal_date="2026-06-18",
        ),
    )

    update_expense(
        conn,
        expense_id,
        Expense(
            name="Car Insurance",
            amount_pence=700_00,
            cadence="yearly",
            renewal_date="2026-07-01",
        ),
    )

    assert get_expense(conn, expense_id).renewal_date == "2026-07-01"
