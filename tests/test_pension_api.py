from fastapi.testclient import TestClient

from app.db import connect, insert_account, insert_pension, list_snapshots
from app.main import app, get_db
from app.projections import Account, Pension


def _client_with_db(conn):
    app.dependency_overrides[get_db] = lambda: conn
    client = TestClient(app)
    return client


def _payload(**overrides) -> dict:
    payload = {
        "name": "Current job",
        "provider": "Smart Pension",
        "employer": "Launchpad",
        "value_pence": 10_000_00,
        "monthly_contribution_pence": 400_00,
        "annual_growth_bp": 0,
        "status": "open",
    }
    payload.update(overrides)
    return payload


def test_get_pensions_is_empty_for_a_fresh_database():
    client = _client_with_db(connect(":memory:"))

    response = client.get("/pensions")

    assert response.status_code == 200
    assert response.json() == []


def test_post_pension_returns_the_created_pot():
    client = _client_with_db(connect(":memory:"))

    response = client.post("/pensions", json=_payload())

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["employer"] == "Launchpad"


def test_a_closed_pot_takes_no_contribution():
    client = _client_with_db(connect(":memory:"))

    response = client.post("/pensions", json=_payload(status="closed"))

    assert response.json()["monthly_contribution_pence"] == 0


def test_a_blank_name_is_rejected():
    client = _client_with_db(connect(":memory:"))

    response = client.post("/pensions", json=_payload(name="   "))

    assert response.status_code == 422


def test_closing_a_pot_keeps_it_in_the_list():
    conn = connect(":memory:")
    client = _client_with_db(conn)
    pension_id = client.post("/pensions", json=_payload()).json()["id"]

    response = client.put(f"/pensions/{pension_id}", json=_payload(status="closed"))

    assert response.json()["status"] == "closed"
    assert len(client.get("/pensions").json()) == 1


def test_updating_an_unknown_pot_returns_404():
    client = _client_with_db(connect(":memory:"))

    response = client.put("/pensions/99", json=_payload())

    assert response.status_code == 404


def test_writing_a_pot_records_a_snapshot():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    client.post("/pensions", json=_payload())

    assert len(list_snapshots(conn)) == 1


def test_pension_projections_honour_custom_months():
    conn = connect(":memory:")
    insert_pension(
        conn,
        Pension(name="Current job", value_pence=1_000_00, annual_growth_bp=1200),
    )
    client = _client_with_db(conn)

    response = client.get("/pension-projections?months=0,12")

    assert response.json() == [
        {"months": 0, "total_pence": 1_000_00},
        {"months": 12, "total_pence": 112_683},
    ]


def test_pension_providers_lists_both_providers_with_logos():
    client = _client_with_db(connect(":memory:"))

    providers = client.get("/pension-providers").json()

    assert [provider["name"] for provider in providers] == [
        "Smart Pension",
        "Royal London",
        "Other",
    ]
    assert providers[0]["logo"] == "/logos/smart-pension.png"


def test_provider_logo_files_are_served():
    client = _client_with_db(connect(":memory:"))

    for logo in ("/logos/smart-pension.png", "/logos/royal-london.png"):
        assert client.get(logo).status_code == 200


def test_a_pot_does_not_move_the_net_wealth_projection():
    conn = connect(":memory:")
    insert_account(conn, Account(name="Cash ISA", balance_pence=1_000_00))
    client = _client_with_db(conn)
    before = client.get("/projections?months=12").json()

    insert_pension(conn, Pension(name="Current job", value_pence=50_000_00))

    assert client.get("/projections?months=12").json() == before


def test_summary_reports_the_pension_total_separately():
    conn = connect(":memory:")
    insert_pension(conn, Pension(name="Current job", value_pence=50_000_00))
    client = _client_with_db(conn)

    summary = client.get("/summary").json()

    assert summary["pension_total_pence"] == 50_000_00
    assert summary["monthly_interest_pence"] == 0
