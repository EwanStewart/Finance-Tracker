import sqlite3

from fastapi.testclient import TestClient

from app.db import connect, insert_account, list_accounts
from app.main import BANKS, app, get_db
from app.projections import Account, default_bank


def _client_with_db(conn):
    app.dependency_overrides[get_db] = lambda: conn
    client = TestClient(app)
    return client


def test_banks_endpoint_lists_moneybox_first_then_rbs():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.get("/banks")

    assert response.status_code == 200
    assert [bank["name"] for bank in response.json()] == ["Moneybox", "RBS"]


def test_banks_endpoint_gives_each_bank_a_logo():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.get("/banks")

    for bank in response.json():
        assert bank["logo"].startswith("/logos/")


def test_bank_logo_files_are_served():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    for bank in BANKS:
        response = client.get(bank["logo"])
        assert response.status_code == 200, bank["logo"]
        assert int(response.headers["content-length"]) > 0


def test_account_keeps_its_bank_through_the_database():
    conn = connect(":memory:")
    insert_account(
        conn,
        Account(name="Cash ISA", balance_pence=2_993_965, bank="Moneybox"),
    )

    assert list_accounts(conn)[0].bank == "Moneybox"


def test_posted_account_keeps_its_bank():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.post(
        "/accounts",
        json={"name": "Lifetime ISA", "balance_pence": 1_572_131, "bank": "Moneybox"},
    )

    assert response.status_code == 201
    assert response.json()["bank"] == "Moneybox"


def test_account_defaults_to_rbs_when_no_bank_is_given():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.post("/accounts", json={"name": "Holiday", "balance_pence": 100})

    assert response.json()["bank"] == "RBS"


def test_unknown_bank_is_rejected():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.post(
        "/accounts",
        json={"name": "Cash ISA", "balance_pence": 100, "bank": "Barclays"},
    )

    assert response.status_code == 422


def test_credit_card_keeps_its_bank():
    conn = connect(":memory:")
    client = _client_with_db(conn)

    response = client.post(
        "/accounts",
        json={
            "name": "Credit Card",
            "balance_pence": 185_821,
            "kind": "credit_card",
            "bank": "RBS",
        },
    )

    assert response.json()["bank"] == "RBS"


LEGACY_ACCOUNTS = """
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance_pence INTEGER NOT NULL,
    annual_rate_bp INTEGER NOT NULL DEFAULT 0,
    monthly_allocation_pence INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL DEFAULT 'savings'
);
INSERT INTO accounts (name, balance_pence, kind) VALUES
    ('Cash ISA', 2993965, 'savings'),
    ('Lifetime ISA', 1572131, 'savings'),
    ('S&S ISA', 1761525, 'savings'),
    ('Reward Savings', 1676984, 'savings'),
    ('Current Account', 165821, 'savings'),
    ('Digital Regular Saver', 500000, 'savings'),
    ('Credit Card', -185821, 'credit_card');
"""


def test_migration_backfills_isas_and_reward_savings_to_moneybox(tmp_path):
    """An existing database predates the bank column, so it must be filled in."""
    path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(str(path))
    legacy.executescript(LEGACY_ACCOUNTS)
    legacy.commit()
    legacy.close()

    banks = {account.name: account.bank for account in list_accounts(connect(path))}

    assert banks == {
        "Cash ISA": "Moneybox",
        "Lifetime ISA": "Moneybox",
        "S&S ISA": "Moneybox",
        "Reward Savings": "Moneybox",
        "Current Account": "RBS",
        "Digital Regular Saver": "RBS",
        "Credit Card": "RBS",
    }


def test_default_bank_puts_isas_and_reward_savings_with_moneybox():
    assert default_bank("Cash ISA") == "Moneybox"
    assert default_bank("S&S ISA") == "Moneybox"
    assert default_bank("Reward Savings") == "Moneybox"


def test_default_bank_puts_everything_else_with_rbs():
    assert default_bank("Current Account") == "RBS"
    assert default_bank("Digital Regular Saver") == "RBS"


def test_default_bank_puts_credit_cards_with_rbs_whatever_they_are_called():
    assert default_bank("Holiday ISA card", kind="credit_card") == "RBS"
