from __future__ import annotations

from datetime import date, timedelta


# 国务院办公厅 2025 / 2026 年部分节假日安排；只在通知已核验的年份推算。
# https://www.forestry.gov.cn/c/www/szxx/594663.jhtml
# https://zwfw.gansu.gov.cn/wenxian/zczx/zwdt/art/2025/art_f430743a887f45109bc8850775c1d89e.html
_HOLIDAY_RANGES = {
    2025: (("01-01", "01-01"), ("01-28", "02-04"), ("04-04", "04-06"),
           ("05-01", "05-05"), ("05-31", "06-02"), ("10-01", "10-08")),
    2026: (("01-01", "01-03"), ("02-15", "02-23"), ("04-04", "04-06"),
           ("05-01", "05-05"), ("06-19", "06-21"), ("09-25", "09-27"),
           ("10-01", "10-07")),
}
_MAKEUP_DAYS = {
    2025: frozenset(("01-26", "02-08", "04-27", "09-28", "10-11")),
    2026: frozenset(("01-04", "02-14", "02-28", "05-09", "09-20", "10-10")),
}


def is_workday(day: date) -> bool | None:
    """Return None when an official schedule for the year has not been loaded."""
    ranges = _HOLIDAY_RANGES.get(day.year)
    if ranges is None:
        return None
    month_day = day.strftime("%m-%d")
    if month_day in _MAKEUP_DAYS[day.year]:
        return True
    if any(start <= month_day <= end for start, end in ranges):
        return False
    return day.weekday() < 5


def next_workday(day: date | str) -> date | None:
    current = date.fromisoformat(day) if isinstance(day, str) else day
    for _ in range(370):
        current += timedelta(days=1)
        result = is_workday(current)
        if result is None:
            return None
        if result:
            return current
    return None
