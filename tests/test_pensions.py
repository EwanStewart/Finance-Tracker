import sqlite3
from dataclasses import replace

from app.db import (
    build_snapshot_payload,
    connect,
    get_pension,
    insert_pension,
    list_pensions,
    update_pension,
)
from app.projections import (
    Pension,
    pension_monthly_contribution,
    pension_total,
    project_pension,
    project_pension_total,
)


def test_an_open_pot_contributes_its_monthly_figure():
    pot = Pension(
        name="Current job", value_pence=10_000_00, monthly_contribution_pence=400_00
    )

    assert pension_monthly_contribution(pot) == 400_00


def test_a_closed_pot_contributes_nothing():
    pot = Pension(
        name="Old job",
        value_pence=10_000_00,
        monthly_contribution_pence=400_00,
        status="closed",
    )

    assert pension_monthly_contribution(pot) == 0


def test_a_closed_pot_still_grows_at_its_rate():
    pot = Pension(
        name="Old job",
        value_pence=1_000_00,
        monthly_contribution_pence=400_00,
        annual_growth_bp=1200,
        status="closed",
    )

    assert project_pension(pot, 12) == 112_683


def test_an_open_pot_grows_on_its_value_and_contributions():
    pot = Pension(
        name="Current job",
        value_pence=1_000_00,
        monthly_contribution_pence=100_00,
        annual_growth_bp=1200,
    )

    assert project_pension(pot, 12) > project_pension(replace(pot, status="closed"), 12)


def test_pension_total_sums_current_values():
    pots = [
        Pension(name="Current job", value_pence=10_000_00),
        Pension(name="Old job", value_pence=2_500_00, status="closed"),
    ]

    assert pension_total(pots) == 12_500_00


def test_project_pension_total_is_zero_without_pots():
    assert project_pension_total([], 12) == 0


def test_project_pension_total_sums_across_pots():
    pots = [
        Pension(name="Current job", value_pence=1_000_00, annual_growth_bp=1200),
        Pension(name="Old job", value_pence=2_000_00, annual_growth_bp=1200),
    ]

    assert project_pension_total(pots, 12) == 112_683 + 225_365


def test_list_pensions_is_empty_for_a_fresh_database():
    conn = connect(":memory:")

    assert list_pensions(conn) == []


def test_an_inserted_pot_comes_back_with_its_id():
    conn = connect(":memory:")
    pot = Pension(
        name="Current job",
        provider="Smart Pension",
        employer="Launchpad",
        value_pence=10_000_00,
        monthly_contribution_pence=400_00,
        annual_growth_bp=500,
    )

    pension_id = insert_pension(conn, pot)

    assert list_pensions(conn) == [replace(pot, id=pension_id)]


def test_closing_a_pot_keeps_the_row():
    conn = connect(":memory:")
    pension_id = insert_pension(conn, Pension(name="Old job", value_pence=2_500_00))

    update_pension(
        conn,
        pension_id,
        Pension(name="Old job", value_pence=2_500_00, status="closed"),
    )

    assert get_pension(conn, pension_id).status == "closed"
    assert len(list_pensions(conn)) == 1


def test_updating_an_unknown_pot_reports_no_change():
    conn = connect(":memory:")

    assert update_pension(conn, 99, Pension(name="Ghost", value_pence=0)) is False


def test_a_database_predating_pensions_gains_an_empty_table(tmp_path):
    path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(str(path))
    legacy.execute(
        "CREATE TABLE accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "name TEXT NOT NULL, balance_pence INTEGER NOT NULL)"
    )
    legacy.commit()
    legacy.close()

    assert list_pensions(connect(path)) == []


def test_snapshot_records_pots_without_moving_the_net_wealth_total():
    conn = connect(":memory:")
    insert_pension(conn, Pension(name="Current job", value_pence=10_000_00))

    payload = build_snapshot_payload(conn)

    assert payload["total_pence"] == 0
    assert payload["pension_total_pence"] == 10_000_00
    assert [pot["name"] for pot in payload["pensions"]] == ["Current job"]
