import datetime

from scripts.monthly_reminder import first_working_day_of_month


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
