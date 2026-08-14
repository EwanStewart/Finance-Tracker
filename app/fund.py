"""Read the Fidelity Index World Fund price from its public factsheet page.

The factsheet is a Next.js page, so the quoted price sits in the __NEXT_DATA__
JSON blob rather than the rendered markup. Fidelity answers requests without a
browser User-Agent with a 403, so the fetch sets one.
"""

import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Any

FUND_ISIN = "GB00BJS8SJ34"
PENCE_CURRENCY = "GBX"
FACTSHEET_URL = (
    "https://www.fidelity.co.uk/factsheet-data/factsheet/"
    "GB00BJS8SJ34-fidelity-index-world-fund-p-acc/key-statistics"
)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)


class FundPriceError(RuntimeError):
    """Raised when the factsheet cannot be read or does not hold a price."""


@dataclass(frozen=True)
class FundPrice:
    isin: str
    name: str
    price_pence: float
    change_pence: float
    change_percent: float
    priced_at: str


def _fund_data(html: str) -> dict[str, Any]:
    match = NEXT_DATA_PATTERN.search(html)
    if match is None:
        raise FundPriceError("factsheet page holds no __NEXT_DATA__ block")
    try:
        page = json.loads(match.group(1))
        result = page["props"]["pageProps"]["initialState"]["fund"]["fundData"]
    except (ValueError, KeyError, TypeError) as error:
        raise FundPriceError("factsheet JSON has an unexpected shape") from error
    return result


def _to_number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise FundPriceError(f"factsheet {field} is not a number: {value!r}") from error
    return result


def parse_price(html: str, isin: str = FUND_ISIN) -> FundPrice:
    fund_data = _fund_data(html)
    details = fund_data.get("priceDtls") or {}
    currency = details.get("currency")
    if currency != PENCE_CURRENCY:
        raise FundPriceError(
            f"factsheet quotes {currency!r}, not {PENCE_CURRENCY}; "
            "the price is no longer in pence"
        )
    result = FundPrice(
        isin=isin,
        name=fund_data.get("name") or fund_data.get("headFundName") or isin,
        price_pence=_to_number(details.get("lastBuySellPrice"), "price"),
        change_pence=_to_number(details.get("changeAbsolute"), "change"),
        change_percent=_to_number(details.get("changePercentage"), "change percent"),
        priced_at=str(details.get("lastUpdated") or ""),
    )
    return result


def fetch_page(url: str = FACTSHEET_URL, timeout: int = 15) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = response.read().decode("utf-8", errors="replace")
    return result


def fetch_price(url: str = FACTSHEET_URL) -> FundPrice:
    return parse_price(fetch_page(url))
