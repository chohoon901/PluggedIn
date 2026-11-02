"""The only station metadata file boundary."""
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from ca.uvic.ecs.csc501.cmn.contracts.models import StationMetadata


_UNCERTAIN_FIELDS = ('accepts_guest_payment', 'has_truck_parking', 'quantity')


def _text(value):
    return value if isinstance(value, str) and value.strip() else None


def _choice(value, choices, default):
    return value if isinstance(value, str) and value in choices else default


def normalize_stations(stations):
    """Validate optional evidence without changing the source document.

    None for aggregateCompleteness records the absence of a valid explicit
    declaration. Snapshot display defaults must never grant an aggregate waiver.
    """
    if not isinstance(stations, dict):
        return {}
    result = {}
    for identifier, entry in stations.items():
        valid_entry = isinstance(entry, dict)
        item = entry if valid_entry else {}
        timezone = _text(item.get('timezone'))
        if timezone is not None:
            try:
                ZoneInfo(timezone)
            except (ValueError, ZoneInfoNotFoundError):
                timezone = None
        unconfirmed = item.get('unconfirmedFields', [] if valid_entry else None)
        valid_fields = isinstance(unconfirmed, list) and all(_text(value) is not None for value in unconfirmed)
        fields = [value for value in unconfirmed if _text(value) is not None] if isinstance(unconfirmed, list) else []
        if not valid_fields:
            fields.extend(_UNCERTAIN_FIELDS)
        result[identifier] = {
            'timezone': timezone,
            'hoursCompleteness': _choice(item.get('hoursCompleteness'), {'COMPLETE', 'PARTIAL', 'UNKNOWN'}, 'UNKNOWN'),
            'portsCompleteness': _choice(item.get('portsCompleteness'), {'COMPLETE', 'PARTIAL', 'UNKNOWN'}, 'UNKNOWN'),
            'aggregateCompleteness': _choice(item.get('aggregateCompleteness'), {'COMPLETE', 'INCOMPLETE'}, None),
            'sourceLabel': _text(item.get('sourceLabel')) or 'Unknown source',
            'sourceUpdatedAt': _text(item.get('sourceUpdatedAt')),
            'unconfirmedFields': list(dict.fromkeys(fields)),
        }
    return result


def read_metadata(settings):
    try:
        content = json.loads(settings.metadata_path.read_text(encoding='utf-8'))
        if not isinstance(content, dict) or type(content.get('schemaVersion')) is not int or content['schemaVersion'] != 1:
            return {}
        return normalize_stations(content.get('stations'))
    except (OSError, ValueError, TypeError):
        return {}


def station_metadata(settings, station_id):
    item = read_metadata(settings).get(str(station_id), {})
    return StationMetadata(
        timezone=item.get('timezone'),
        hours_completeness=item.get('hoursCompleteness', 'UNKNOWN'),
        ports_completeness=item.get('portsCompleteness', 'UNKNOWN'),
        aggregate_completeness=item.get('aggregateCompleteness') or 'INCOMPLETE',
        source_label=item.get('sourceLabel') or 'Unknown source',
        source_updated_at=item.get('sourceUpdatedAt'),
        unconfirmed_fields=tuple(item.get('unconfirmedFields') or ()),
    )
