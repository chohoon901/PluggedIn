"""Translate explicit UI wall-clock choices into the existing aware-time contract."""
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from ca.uvic.ecs.csc501.cmn.application.services import parse_arrival
from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError

DEFAULT_ARRIVAL_TIMEZONE = "America/Vancouver"
ARRIVAL_TIMEZONES = {"America/Vancouver": "Pacific time (British Columbia)", "UTC": "UTC"}


def _zone(name):
    if name not in ARRIVAL_TIMEZONES:
        raise InputError("Choose a supported time zone.", {"arrival_timezone": "Choose Pacific time or UTC."})
    return ZoneInfo(name)


def resolve_arrival(arrival_at="", arrival_date="", arrival_time="", arrival_timezone=DEFAULT_ARRIVAL_TIMEZONE, search_now=""):
    zone = _zone(arrival_timezone)
    if search_now == "1":
        return None
    if not arrival_date and not arrival_time:
        return arrival_at or None
    if not arrival_date or not arrival_time:
        missing = "arrival_time" if arrival_date else "arrival_date"
        raise InputError("Choose both an arrival date and time.", {missing: "Choose a date and time, or use Search now."})
    try:
        day = date.fromisoformat(arrival_date)
        clock = time.fromisoformat(arrival_time)
        if clock.tzinfo is not None:
            raise ValueError
        wall_time = datetime.combine(day, clock)
        candidates = set()
        for fold in (0, 1):
            instant = wall_time.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
            if instant.astimezone(zone).replace(tzinfo=None) == wall_time:
                candidates.add(instant)
    except (ValueError, TypeError, OverflowError):
        raise InputError("Check the arrival date and time.", {"arrival_date": "Choose a valid date.", "arrival_time": "Choose a valid time."}) from None
    if not candidates:
        raise InputError("This local time does not exist because the clocks move forward.", {"arrival_time": "Choose another time."})
    if len(candidates) > 1:
        raise InputError("This local time occurs twice because the clocks move back.", {"arrival_time": "Choose another time, or select UTC to specify the exact time."})
    return candidates.pop().isoformat()


def arrival_form_values(instant, zone_name=DEFAULT_ARRIVAL_TIMEZONE):
    zone = _zone(zone_name)
    try:
        local = parse_arrival(instant).astimezone(zone)
        return {"arrival_date": local.date().isoformat(), "arrival_time": local.strftime("%H:%M"), "arrival_timezone": zone_name}
    except (InputError, OverflowError, ValueError):
        return {"arrival_date": "", "arrival_time": "", "arrival_timezone": zone_name}


def friendly_datetime(value, zone_name=DEFAULT_ARRIVAL_TIMEZONE):
    try:
        local = parse_arrival(value).astimezone(_zone(zone_name))
        month = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[local.month - 1]
        clock = f"{local.hour % 12 or 12}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"
        offset = local.strftime("%z")
        label = "Pacific time" if zone_name == DEFAULT_ARRIVAL_TIMEZONE else "UTC"
        return f"{month} {local.day}, {local.year} at {clock} · {label} (UTC{offset[:3]}:{offset[3:]})"
    except (InputError, ValueError, OverflowError, TypeError):
        return "Local time unavailable"
