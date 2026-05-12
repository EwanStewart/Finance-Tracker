from app.db import (
    capture_snapshot,
    connect,
    delete_snapshot,
    insert_account,
    insert_expense,
    insert_income_source,
    insert_snapshot,
    list_snapshots,
)
from app.projections import Account, Expense, IncomeSource, Snapshot


def test_insert_snapshot_stores_fields_and_returns_id():
    conn = connect(":memory:")
    payload = {"accounts": [], "income": [], "expenses": [], "total_pence": 0}

    snap_id = insert_snapshot(
        conn,
        Snapshot(
            taken_at="2026-05-12T09:00:00Z",
            payload=payload,
            trigger="Manual",
            label="opening",
        ),
    )

    snapshots = list_snapshots(conn)
    assert snap_id == snapshots[0].id
    assert snapshots == [
        Snapshot(
            taken_at="2026-05-12T09:00:00Z",
            payload=payload,
            trigger="Manual",
            label="opening",
            id=snap_id,
        )
    ]


def test_list_snapshots_orders_chronologically():
    conn = connect(":memory:")
    insert_snapshot(conn, Snapshot(taken_at="2026-05-12T09:01:00Z", payload={}))
    insert_snapshot(conn, Snapshot(taken_at="2026-05-12T09:00:00Z", payload={}))

    snapshots = list_snapshots(conn)

    assert [s.taken_at for s in snapshots] == [
        "2026-05-12T09:00:00Z",
        "2026-05-12T09:01:00Z",
    ]


def test_delete_snapshot_returns_true_when_present():
    conn = connect(":memory:")
    snap_id = insert_snapshot(
        conn, Snapshot(taken_at="2026-05-12T09:00:00Z", payload={})
    )

    deleted = delete_snapshot(conn, snap_id)

    assert deleted is True
    assert list_snapshots(conn) == []


def test_delete_snapshot_returns_false_when_missing():
    conn = connect(":memory:")

    deleted = delete_snapshot(conn, 99)

    assert deleted is False


def test_capture_snapshot_includes_full_state():
    conn = connect(":memory:")
    insert_account(conn, Account(name="Cash ISA", balance_pence=1_000_00))
    insert_income_source(conn, IncomeSource(name="Salary", monthly_amount_pence=3_000_00))
    insert_expense(
        conn, Expense(name="Rent", amount_pence=900_00, cadence="monthly")
    )

    snapshot = capture_snapshot(
        conn, trigger="Manual", now_fn=lambda: "2026-05-12T09:00:00Z"
    )

    assert snapshot.taken_at == "2026-05-12T09:00:00Z"
    assert snapshot.trigger == "Manual"
    payload = snapshot.payload
    assert len(payload["accounts"]) == 1
    assert payload["accounts"][0]["name"] == "Cash ISA"
    assert payload["income"][0]["name"] == "Salary"
    assert payload["expenses"][0]["name"] == "Rent"
    assert payload["total_pence"] == 1_000_00


def test_capture_snapshot_write_inside_window_updates_latest():
    conn = connect(":memory:")
    capture_snapshot(conn, trigger="Write", now_fn=lambda: "2026-05-12T09:00:00Z")
    insert_account(conn, Account(name="Added", balance_pence=500))

    capture_snapshot(
        conn,
        trigger="Write",
        now_fn=lambda: "2026-05-12T09:00:30Z",
        debounce_seconds=60,
    )

    snapshots = list_snapshots(conn)
    assert len(snapshots) == 1
    assert snapshots[0].taken_at == "2026-05-12T09:00:30Z"
    assert snapshots[0].payload["total_pence"] == 500


def test_capture_snapshot_write_after_window_inserts_new():
    conn = connect(":memory:")
    capture_snapshot(conn, trigger="Write", now_fn=lambda: "2026-05-12T09:00:00Z")

    capture_snapshot(
        conn,
        trigger="Write",
        now_fn=lambda: "2026-05-12T09:02:00Z",
        debounce_seconds=60,
    )

    assert len(list_snapshots(conn)) == 2


def test_capture_snapshot_manual_always_inserts():
    conn = connect(":memory:")
    capture_snapshot(conn, trigger="Write", now_fn=lambda: "2026-05-12T09:00:00Z")

    capture_snapshot(
        conn,
        trigger="Manual",
        label="pay day",
        now_fn=lambda: "2026-05-12T09:00:30Z",
        debounce_seconds=60,
    )

    snapshots = list_snapshots(conn)
    assert len(snapshots) == 2
    assert snapshots[1].trigger == "Manual"
    assert snapshots[1].label == "pay day"


def test_capture_snapshot_write_does_not_replace_manual_within_window():
    conn = connect(":memory:")
    capture_snapshot(
        conn,
        trigger="Manual",
        label="opening",
        now_fn=lambda: "2026-05-12T09:00:00Z",
    )

    capture_snapshot(
        conn,
        trigger="Write",
        now_fn=lambda: "2026-05-12T09:00:30Z",
        debounce_seconds=60,
    )

    snapshots = list_snapshots(conn)
    assert len(snapshots) == 2
    assert snapshots[0].trigger == "Manual"
    assert snapshots[0].label == "opening"
    assert snapshots[1].trigger == "Write"
