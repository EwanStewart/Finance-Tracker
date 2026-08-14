import sqlite3
from dataclasses import replace

from app.db import (
    connect,
    delete_account,
    get_account,
    insert_account,
    list_accounts,
    list_snapshots,
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


def test_account_kind_defaults_to_savings():
    conn = connect(":memory:")
    account_id = insert_account(conn, Account(name="ISA", balance_pence=100_00))

    assert get_account(conn, account_id).kind == "savings"


def test_account_kind_credit_card_round_trips():
    conn = connect(":memory:")
    account_id = insert_account(
        conn, Account(name="Visa", balance_pence=-100_00, kind="credit_card")
    )

    assert get_account(conn, account_id).kind == "credit_card"


def test_kind_migration_adds_column_to_legacy_database(tmp_path):
    db = tmp_path / "legacy.db"
    raw = sqlite3.connect(db)
    raw.executescript(
        "CREATE TABLE accounts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL,"
        "balance_pence INTEGER NOT NULL,"
        "annual_rate_bp INTEGER NOT NULL DEFAULT 0,"
        "monthly_allocation_pence INTEGER NOT NULL DEFAULT 0"
        ");"
        "INSERT INTO accounts (name, balance_pence) VALUES ('Pre-migration', 100);"
    )
    raw.commit()
    raw.close()

    conn = connect(db)

    accounts = list_accounts(conn)
    assert len(accounts) == 1
    assert accounts[0].kind == "savings"


LEGACY_SNAPSHOT_SCHEMA = (
    "CREATE TABLE snapshots ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "taken_at TEXT NOT NULL,"
    "trigger TEXT NOT NULL DEFAULT 'manual'"
    " CHECK (trigger IN ('manual', 'write')),"
    "label TEXT,"
    "payload TEXT NOT NULL"
    ");"
    "CREATE INDEX idx_snapshots_taken_at ON snapshots(taken_at);"
    "INSERT INTO snapshots (id, taken_at, trigger, label, payload) VALUES "
    "(1, '2026-01-01T00:00:00Z', 'manual', 'New year', '{\"total_pence\": 5}'),"
    "(2, '2026-01-02T00:00:00Z', 'write', NULL, '{\"total_pence\": 7}');"
)


def test_trigger_case_migration_keeps_every_snapshot(tmp_path):
    db = tmp_path / "legacy.db"
    raw = sqlite3.connect(db)
    raw.executescript(LEGACY_SNAPSHOT_SCHEMA)
    raw.commit()
    raw.close()

    snapshots = list_snapshots(connect(db))

    assert [(s.id, s.trigger, s.label) for s in snapshots] == [
        (1, "Manual", "New year"),
        (2, "Write", None),
    ]
    assert snapshots[1].payload == {"total_pence": 7}


def test_trigger_case_migration_leaves_a_migrated_database_alone(tmp_path):
    db = tmp_path / "legacy.db"
    raw = sqlite3.connect(db)
    raw.executescript(LEGACY_SNAPSHOT_SCHEMA)
    raw.commit()
    raw.close()
    connect(db).close()

    snapshots = list_snapshots(connect(db))

    assert len(snapshots) == 2
