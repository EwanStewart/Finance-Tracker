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


def render_email(today: datetime.date) -> tuple[str, str, str]:
    last_month = (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%B")
    this_month = today.strftime("%B %Y")
    subject = f"Finance Tracker: snapshot reminder for {this_month}"
    text = (
        f"It's the first working day of {this_month}.\n\n"
        "Open https://finance.local, switch to the History tab, "
        "and click Snapshot now to capture this month's state.\n\n"
        f"Suggested label: \"End of {last_month}\"."
    )
    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f5f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1a1a1a;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f6f8;padding:32px 16px;">
<tr><td align="center">
  <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
    <tr><td style="background:#0a2240;padding:20px 24px;border-radius:6px 6px 0 0;border-bottom:4px solid #5a287d;">
      <div style="color:#ffffff;font-size:18px;font-weight:600;letter-spacing:0.2px;">Finance Tracker</div>
    </td></tr>
    <tr><td style="background:#ffffff;border:1px solid #e3e6ea;border-top:0;padding:32px 24px;">
      <h1 style="margin:0 0 12px;font-size:22px;color:#0a2240;font-weight:600;">Time for a monthly snapshot</h1>
      <p style="margin:0 0 16px;color:#1a1a1a;line-height:1.55;font-size:15px;">
        It's the first working day of {this_month}. Capture this month's state so the history chart stays honest.
      </p>
      <p style="margin:0 0 28px;color:#5f6770;font-size:14px;line-height:1.5;">
        Suggested label: <span style="color:#1a1a1a;font-weight:600;">End of {last_month}</span>
      </p>
      <a href="https://finance.local/#history" style="display:inline-block;background:#0a2240;color:#ffffff;text-decoration:none;padding:12px 22px;border-radius:4px;font-weight:600;font-size:14px;">Open History tab</a>
    </td></tr>
    <tr><td style="padding:16px 24px;color:#5f6770;font-size:12px;text-align:center;">
      Sent by the Finance Tracker monthly reminder workflow.
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""
    return subject, text, html


def send_email(api_key: str, from_addr: str, to_addr: str, today: datetime.date) -> None:
    subject, text, html = render_email(today)
    payload = {
        "from": from_addr,
        "to": [to_addr],
        "subject": subject,
        "text": text,
        "html": html,
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
    force = os.environ.get("FORCE_SEND", "").lower() == "true"
    if not force:
        holidays = fetch_bank_holidays()
        target = first_working_day_of_month(today.year, today.month, holidays)
        if today != target:
            print(f"today {today.isoformat()} != first working day {target.isoformat()}; skipping")
            return 0
    else:
        print("FORCE_SEND set; bypassing date check")
    api_key = os.environ["RESEND_API_KEY"]
    from_addr = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
    to_addr = os.environ["TO_EMAIL"]
    send_email(api_key, from_addr, to_addr, today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
