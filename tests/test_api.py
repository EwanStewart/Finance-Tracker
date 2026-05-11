from fastapi.testclient import TestClient

from app.db import connect, insert_account
from app.main import app, get_db
from app.projections import Account


def _client_with_db(conn):
    app.dependency_overrides[get_db] = lambda: conn
    client = TestClient(app)
    return client


def test_get_accounts_is_empty_for_fresh_database():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.get("/accounts")

    assert response.status_code == 200
    assert response.json() == []


def test_get_accounts_returns_inserted_accounts():
    conn = connect(":memory:")
    insert_account(
        conn,
        Account(
            name="Cash ISA",
            balance_pence=29_939_65,
            annual_rate_bp=345,
            monthly_allocation_pence=0,
        ),
    )
    client = _client_with_db(conn)

    response = client.get("/accounts")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "Cash ISA",
            "balance_pence": 2_993_965,
            "annual_rate_bp": 345,
            "monthly_allocation_pence": 0,
            "id": 1,
        }
    ]


def test_get_projections_returns_total_for_each_month():
    conn = connect(":memory:")
    insert_account(conn, Account(name="A", balance_pence=100_00))
    insert_account(
        conn,
        Account(name="B", balance_pence=200_00, monthly_allocation_pence=10_00),
    )
    client = _client_with_db(conn)

    response = client.get("/projections?months=0,12")

    assert response.status_code == 200
    assert response.json() == [
        {"months": 0, "total_pence": 100_00 + 200_00},
        {"months": 12, "total_pence": 100_00 + 200_00 + 12 * 10_00},
    ]


def test_get_projections_uses_default_horizons_when_no_param():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.get("/projections")

    assert response.status_code == 200
    returned_months = [point["months"] for point in response.json()]
    assert returned_months == [0, 1, 3, 6, 12, 24, 60]


def test_index_serves_html_with_chart_canvas():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<canvas id="chart"' in response.text


def test_post_account_creates_and_returns_with_id():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.post(
        "/accounts",
        json={"name": "New Card", "balance_pence": -1000, "annual_rate_bp": 0},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["name"] == "New Card"
    assert body["balance_pence"] == -1000


def test_put_account_updates_existing():
    conn = connect(":memory:")
    insert_account(conn, Account(name="Old", balance_pence=100_00))
    client = _client_with_db(conn)

    response = client.put(
        "/accounts/1",
        json={"name": "Renamed", "balance_pence": 250_00},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["balance_pence"] == 250_00


def test_put_account_returns_404_when_missing():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.put(
        "/accounts/99",
        json={"name": "Nope", "balance_pence": 0},
    )

    assert response.status_code == 404


def test_delete_account_returns_204():
    conn = connect(":memory:")
    insert_account(conn, Account(name="Gone", balance_pence=0))
    client = _client_with_db(conn)

    response = client.delete("/accounts/1")

    assert response.status_code == 204


def test_delete_account_returns_404_when_missing():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.delete("/accounts/99")

    assert response.status_code == 404
