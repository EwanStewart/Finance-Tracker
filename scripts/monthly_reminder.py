"""Send a monthly snapshot reminder email via Resend on the first UK working day.

Designed to run from a GitHub Actions cron schedule once per weekday morning.
The script checks the gov.uk bank holidays feed to skip public holidays, and
only sends if today is the first working day of the calendar month across
all three UK regions.
"""

import datetime
import json
import os
import sys
import urllib.request


GOV_UK_BANK_HOLIDAYS_URL = "https://www.gov.uk/bank-holidays.json"
RESEND_ENDPOINT = "https://api.resend.com/emails"
REGIONS = ("england-and-wales", "scotland", "northern-ireland")


def fetch_bank_holidays(
    url: str = GOV_UK_BANK_HOLIDAYS_URL, regions=REGIONS
) -> set[str]:
    with urllib.request.urlopen(url, timeout=15) as response:
        data = json.load(response)
    holidays = {
        event["date"] for region in regions for event in data[region]["events"]
    }
    return holidays


def is_working_day(day: datetime.date, holidays: set[str]) -> bool:
    return day.weekday() < 5 and day.isoformat() not in holidays


def first_working_day_of_month(year: int, month: int, holidays: set[str]) -> datetime.date:
    day = datetime.date(year, month, 1)
    while not is_working_day(day, holidays):
        day += datetime.timedelta(days=1)
    return day


def today_in_london() -> datetime.date:
    from zoneinfo import ZoneInfo

    return datetime.datetime.now(ZoneInfo("Europe/London")).date()


def send_email(api_key: str, from_addr: str, to_addr: str, today: datetime.date) -> None:
    payload = {
        "from": from_addr,
        "to": [to_addr],
        "subject": f"Finance Tracker: snapshot reminder for {today.strftime('%B %Y')}",
        "text": (
            "It's the first working day of the month.\n\n"
            "Open https://finance.local, switch to the History tab, "
            "and click Snapshot now to capture this month's state.\n\n"
            f"Suggested label: \"End of {(today - datetime.timedelta(days=1)).strftime('%B')}\".\n"
        ),
    }
    request = urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        print(f"resend status={response.status} body={response.read().decode()}")


def main() -> int:
    today = today_in_london()
    holidays = fetch_bank_holidays()
    target = first_working_day_of_month(today.year, today.month, holidays)
    if today != target:
        print(f"today {today.isoformat()} != first working day {target.isoformat()}; skipping")
        return 0
    api_key = os.environ["RESEND_API_KEY"]
    from_addr = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
    to_addr = os.environ["TO_EMAIL"]
    send_email(api_key, from_addr, to_addr, today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
