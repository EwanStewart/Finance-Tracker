from fastapi.testclient import TestClient

from app.db import connect, insert_snapshot, list_snapshots
from app.main import app, get_db
from app.projections import Snapshot


def _client_with_db(conn):
    app.dependency_overrides[get_db] = lambda: conn
    client = TestClient(app)
    return client


def test_post_snapshot_creates_manual_entry():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.post("/snapshots", json={"label": "pay day"})

    assert response.status_code == 201
    body = response.json()
    assert body["trigger"] == "Manual"
    assert body["label"] == "pay day"
    assert "taken_at" in body
    assert body["payload"]["total_pence"] == 0


def test_post_snapshot_accepts_empty_body():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.post("/snapshots", json={})

    assert response.status_code == 201
    assert response.json()["trigger"] == "Manual"


def test_get_snapshots_returns_chronological_list():
    conn = connect(":memory:")
    insert_snapshot(
        conn, Snapshot(taken_at="2026-05-12T09:01:00Z", payload={"total_pence": 200})
    )
    insert_snapshot(
        conn, Snapshot(taken_at="2026-05-12T09:00:00Z", payload={"total_pence": 100})
    )
    client = _client_with_db(conn)

    response = client.get("/snapshots")

    assert response.status_code == 200
    body = response.json()
    assert [s["taken_at"] for s in body] == [
        "2026-05-12T09:00:00Z",
        "2026-05-12T09:01:00Z",
    ]


def test_delete_snapshot_returns_204():
    conn = connect(":memory:")
    snap_id = insert_snapshot(
        conn, Snapshot(taken_at="2026-05-12T09:00:00Z", payload={})
    )
    client = _client_with_db(conn)

    response = client.delete(f"/snapshots/{snap_id}")

    assert response.status_code == 204
    assert list_snapshots(conn) == []


def test_delete_snapshot_returns_404_when_missing():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.delete("/snapshots/99")

    assert response.status_code == 404


def test_creating_account_triggers_snapshot():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    client.post(
        "/accounts", json={"name": "Cash ISA", "balance_pence": 100_00}
    )

    snapshots = list_snapshots(conn)
    assert len(snapshots) == 1
    assert snapshots[0].trigger == "Write"
    assert snapshots[0].payload["total_pence"] == 100_00


def test_updating_income_triggers_snapshot():
    conn = connect(":memory:")
    client = _client_with_db(conn)
    created = client.post(
        "/income", json={"name": "Salary", "monthly_amount_pence": 3_000_00}
    ).json()

    client.put(
        f"/income/{created['id']}",
        json={"name": "Salary", "monthly_amount_pence": 3_100_00},
    )

    snapshots = list_snapshots(conn)
    assert len(snapshots) == 1
    latest_income = snapshots[0].payload["income"][0]
    assert latest_income["monthly_amount_pence"] == 3_100_00


def test_deleting_expense_triggers_snapshot():
    conn = connect(":memory:")
    client = _client_with_db(conn)
    created = client.post(
        "/expenses",
        json={"name": "Gym", "amount_pence": 30_00, "cadence": "monthly"},
    ).json()

    client.delete(f"/expenses/{created['id']}")

    snapshots = list_snapshots(conn)
    assert snapshots[-1].payload["expenses"] == []
