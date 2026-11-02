"""Presentation-only context composition and form validation."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from ca.uvic.ecs.csc501.cmn.contracts.errors import AppError, InputError
from .arrival import ARRIVAL_TIMEZONES, DEFAULT_ARRIVAL_TIMEZONE, friendly_datetime

templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))
templates.env.filters['friendly_datetime'] = friendly_datetime
STATUS_LABELS = {'AVAILABLE': 'Available', 'NEEDS_REVIEW': 'Needs review', 'UNAVAILABLE': 'Unavailable', 'PASS': 'Pass', 'UNKNOWN': 'Needs review', 'FAIL': 'Not met'}
CHECK_LABELS = {'opening': 'Opening hours', 'access': 'Site & vehicle access', 'connector': 'Direct connection', 'payment': 'Payment'}
DISCLAIMER = 'Estimates based on public and registered data. Live faults, queues and occupancy are not included. Road access and full vehicle clearance are unverified. Power limits do not guarantee actual charging speed.'
DEFAULT_BBOX = {'west': '-123.50', 'south': '48.35', 'east': '-123.20', 'north': '48.60'}


def now_string():
    return datetime.now(timezone.utc).isoformat()


def render(request: Request, name: str, context: dict | None = None, status_code=200):
    return templates.TemplateResponse(request=request, name=name, context={
        'request': request, 'status_labels': STATUS_LABELS, 'check_labels': CHECK_LABELS,
        'disclaimer': DISCLAIMER, 'errors': {}, 'arrival_timezones': ARRIVAL_TIMEZONES,
        'arrival_timezone': DEFAULT_ARRIVAL_TIMEZONE, **(context or {}),
    }, status_code=status_code)


def validation_fields(exc):
    fields = {}
    for error in exc.errors():
        location = '.'.join(str(item) for item in error['loc'] if item not in ('body', 'query', 'path')) or 'form'
        fields[location] = error['msg']
    return fields


def validated(schema, data):
    try:
        return schema.model_validate(data).model_dump(mode='json')
    except ValidationError as exc:
        raise InputError('Please check your entries.', field_errors=validation_fields(exc)) from exc


def form_page(request, services, kind, values=None, errors=None, item_id=None, status_code=200):
    context = {'values': values or {}, 'errors': errors or {}, 'item_id': item_id, 'kind': kind}
    if kind == 'vehicles':
        context['connectors'] = services.catalog()['connectors']
    if kind == 'memberships':
        context['drivers'] = services.list_drivers()
        context['networks'] = services.catalog()['networks']
    return render(request, f'{kind}/form.html', context, status_code)


def save_form(request, services, kind, schema, values, item_id=None):
    try:
        data = validated(schema, values)
        getattr(services, f'save_{kind[:-1]}')(data, item_id)
    except AppError as exc:
        if exc.status_code not in (400, 409):
            raise
        return form_page(request, services, kind, values, exc.field_errors or {'form': exc.message}, item_id, 400)
    from fastapi.responses import RedirectResponse
    return RedirectResponse('/' + kind, status_code=303)


def selection_context(services):
    return {'drivers': services.list_drivers(), 'vehicles': services.list_vehicles()}


def result_context(result, driver_id, vehicle_id, arrival_at, arrival_timezone=DEFAULT_ARRIVAL_TIMEZONE):
    query = urlencode({'driver_id': driver_id, 'vehicle_id': vehicle_id, 'arrival_at': arrival_at, 'arrival_timezone': arrival_timezone})
    station = result['station']
    return {**result, 'arrival_timezone': arrival_timezone, 'detail_url': f"/stations/{result['station_id']}?{query}",
            'directions_url': 'https://www.google.com/maps/dir/?' + urlencode({'api': 1, 'destination': f"{station['latitude']},{station['longitude']}"})}
