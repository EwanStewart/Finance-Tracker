import json

import pytest

from app.fund import FUND_ISIN, FundPriceError, parse_price


def build_page(price="471.25", change="2.14", percent="0.46", currency="GBX") -> str:
    payload = {
        "props": {
            "pageProps": {
                "initialState": {
                    "fund": {
                        "fundData": {
                            "name": "Fidelity Index World Fund P Accumulation",
                            "priceDtls": {
                                "lastBuySellPrice": price,
                                "changeAbsolute": change,
                                "changePercentage": percent,
                                "lastUpdated": "2026-08-13 01:00:00",
                                "currency": currency,
                            },
                        }
                    }
                }
            }
        }
    }
    return (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}"
        "</script></body></html>"
    )


def test_parse_price_reads_the_next_data_block():
    price = parse_price(build_page())
    assert price.isin == FUND_ISIN
    assert price.name == "Fidelity Index World Fund P Accumulation"
    assert price.price_pence == pytest.approx(471.25)
    assert price.change_pence == pytest.approx(2.14)
    assert price.change_percent == pytest.approx(0.46)
    assert price.priced_at == "2026-08-13 01:00:00"


def test_parse_price_rejects_a_page_without_the_next_data_block():
    with pytest.raises(FundPriceError):
        parse_price("<html><body>no data here</body></html>")


def test_parse_price_rejects_a_non_numeric_price():
    with pytest.raises(FundPriceError):
        parse_price(build_page(price="null"))


def test_parse_price_rejects_a_currency_that_is_not_pence():
    with pytest.raises(FundPriceError):
        parse_price(build_page(currency="GBP"))
