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
