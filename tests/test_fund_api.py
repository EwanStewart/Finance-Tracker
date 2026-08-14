from urllib.error import URLError

import pytest
from fastapi.testclient import TestClient

from app import main
from app.db import connect, save_fund_price
from app.fund import FUND_ISIN, FundPrice, FundPriceError
from app.main import app, get_db

LIVE = FundPrice(
    isin=FUND_ISIN,
    name="Fidelity Index World Fund P Accumulation",
    price_pence=471.25,
    change_pence=2.14,
    change_percent=0.46,
    priced_at="2026-08-13 01:00:00",
)
CACHED = FundPrice(
    isin=FUND_ISIN,
    name="Fidelity Index World Fund P Accumulation",
    price_pence=469.11,
    change_pence=-1.02,
    change_percent=-0.22,
    priced_at="2026-08-12 01:00:00",
)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _client(conn, monkeypatch, today="2026-08-13", fetcher=None):
    app.dependency_overrides[get_db] = lambda: conn
    monkeypatch.setattr(main, "_today_in_london", lambda: today)
    if fetcher is not None:
        monkeypatch.setattr(main, "fetch_price", fetcher)
    return TestClient(app)


def _fetcher_returning(price, calls):
    def fetch():
        calls.append(1)
        return price

    return fetch


def _fetcher_failing(calls, error=None):
    def fetch():
        calls.append(1)
        raise error or FundPriceError("factsheet unavailable")

    return fetch


def test_fund_price_fetches_and_caches_when_no_entry_exists(monkeypatch):
    conn = connect(":memory:")
    calls = []
    client = _client(conn, monkeypatch, fetcher=_fetcher_returning(LIVE, calls))

    response = client.get("/fund-price")

    assert response.status_code == 200
    body = response.json()
    assert body["price_pence"] == pytest.approx(471.25)
    assert body["change_percent"] == pytest.approx(0.46)
    assert body["priced_at"] == "2026-08-13 01:00:00"
    assert body["stale"] is False
    assert body["source_url"].startswith("https://www.fidelity.co.uk/")
    assert len(calls) == 1


def test_fund_price_serves_the_cache_without_refetching_on_the_same_day(monkeypatch):
    conn = connect(":memory:")
    save_fund_price(conn, CACHED, fetched_on="2026-08-13")
    calls = []
    client = _client(conn, monkeypatch, fetcher=_fetcher_returning(LIVE, calls))

    body = client.get("/fund-price").json()

    assert body["price_pence"] == pytest.approx(469.11)
    assert calls == []


def test_fund_price_refetches_once_the_cached_day_has_passed(monkeypatch):
    conn = connect(":memory:")
    save_fund_price(conn, CACHED, fetched_on="2026-08-12")
    calls = []
    client = _client(conn, monkeypatch, fetcher=_fetcher_returning(LIVE, calls))

    body = client.get("/fund-price").json()

    assert body["price_pence"] == pytest.approx(471.25)
    assert body["stale"] is False
    assert len(calls) == 1


@pytest.mark.parametrize(
    "error",
    [FundPriceError("factsheet unavailable"), URLError("network is down")],
)
def test_fund_price_falls_back_to_the_stale_cache_when_the_fetch_fails(
    monkeypatch, error
):
    conn = connect(":memory:")
    save_fund_price(conn, CACHED, fetched_on="2026-08-12")
    client = _client(conn, monkeypatch, fetcher=_fetcher_failing([], error))

    response = client.get("/fund-price")

    assert response.status_code == 200
    body = response.json()
    assert body["price_pence"] == pytest.approx(469.11)
    assert body["stale"] is True


def test_fund_price_reports_unavailable_when_there_is_nothing_to_fall_back_on(
    monkeypatch,
):
    conn = connect(":memory:")
    client = _client(conn, monkeypatch, fetcher=_fetcher_failing([]))

    response = client.get("/fund-price")

    assert response.status_code == 503
