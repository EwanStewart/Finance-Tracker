import datetime

from scripts import monthly_reminder
from scripts.monthly_reminder import first_working_day_of_month, render_email


def test_first_working_day_when_month_starts_on_weekday():
    # 1 June 2026 is a Monday with no UK bank holidays.
    assert first_working_day_of_month(2026, 6, set()) == datetime.date(2026, 6, 1)


def test_first_working_day_skips_weekend_at_start_of_month():
    # 1 Aug 2026 is a Saturday, 2 Aug is Sunday, 3 Aug is Monday.
    assert first_working_day_of_month(2026, 8, set()) == datetime.date(2026, 8, 3)


def test_first_working_day_skips_bank_holiday():
    # 1 Jan 2026 is a Thursday, but New Year's Day is a UK bank holiday.
    holidays = {"2026-01-01"}
    assert first_working_day_of_month(2026, 1, holidays) == datetime.date(2026, 1, 2)


def test_first_working_day_skips_weekend_then_bank_holiday():
    # 1 May 2027 = Sat, 2 May = Sun, 3 May = Mon and treated as a bank holiday.
    holidays = {"2027-05-03"}
    assert first_working_day_of_month(2027, 5, holidays) == datetime.date(2027, 5, 4)


def test_render_email_includes_month_and_label_for_previous_month():
    subject, text, html = render_email(datetime.date(2026, 6, 1))
    assert "June 2026" in subject
    assert "June 2026" in text
    assert "End of May" in text
    assert "June 2026" in html
    assert "End of May" in html
    assert "#0a2240" in html
    assert "#5a287d" in html


def test_should_send_only_on_the_first_working_day(monkeypatch):
    holidays = {"2026-09-01"}
    monkeypatch.setattr(monthly_reminder, "fetch_bank_holidays", lambda: holidays)

    assert monthly_reminder.should_send(datetime.date(2026, 9, 2), force=False) is True
    assert monthly_reminder.should_send(datetime.date(2026, 9, 3), force=False) is False


def test_should_send_bypasses_the_date_check_when_forced(monkeypatch):
    def unreachable():
        raise AssertionError("holidays should not be fetched when forced")

    monkeypatch.setattr(monthly_reminder, "fetch_bank_holidays", unreachable)

    assert monthly_reminder.should_send(datetime.date(2026, 9, 3), force=True) is True
