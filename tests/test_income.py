from dataclasses import replace

from app.db import (
    connect,
    delete_income_source,
    get_income_source,
    insert_income_source,
    list_income_sources,
    update_income_source,
)
from app.projections import IncomeSource


def test_list_income_sources_is_empty_for_fresh_database():
    conn = connect(":memory:")

    assert list_income_sources(conn) == []


def test_inserted_income_source_is_returned_with_id():
    conn = connect(":memory:")
    source = IncomeSource(name="Salary", monthly_amount_pence=2_954_00)

    source_id = insert_income_source(conn, source)

    assert list_income_sources(conn) == [replace(source, id=source_id)]


def test_get_income_source_returns_none_when_missing():
    conn = connect(":memory:")

    assert get_income_source(conn, 99) is None


def test_update_income_source_modifies_existing_row():
    conn = connect(":memory:")
    source_id = insert_income_source(
        conn, IncomeSource(name="Salary", monthly_amount_pence=2_954_00)
    )

    changed = update_income_source(
        conn, source_id, IncomeSource(name="Salary", monthly_amount_pence=3_100_00)
    )

    assert changed is True
    assert get_income_source(conn, source_id).monthly_amount_pence == 3_100_00


def test_update_income_source_returns_false_when_missing():
    conn = connect(":memory:")

    changed = update_income_source(
        conn, 99, IncomeSource(name="X", monthly_amount_pence=0)
    )

    assert changed is False


def test_delete_income_source_removes_row():
    conn = connect(":memory:")
    source_id = insert_income_source(
        conn, IncomeSource(name="Salary", monthly_amount_pence=2_954_00)
    )

    deleted = delete_income_source(conn, source_id)

    assert deleted is True
    assert get_income_source(conn, source_id) is None


def test_delete_income_source_returns_false_when_missing():
    conn = connect(":memory:")

    assert delete_income_source(conn, 99) is False
