from fastapi import APIRouter, Depends, Request
from ca.uvic.ecs.csc501.cmn.contracts.errors import AppError
from ..dependencies import get_services
from ..schemas import EvaluationInput, SearchInput
from ..views import DEFAULT_BBOX, render, result_context, selection_context, validated
from ..arrival import DEFAULT_ARRIVAL_TIMEZONE, arrival_form_values, resolve_arrival

router = APIRouter()


@router.get('/stations')
def stations(request: Request, driver_id: str = '', vehicle_id: str = '', arrival_at: str = '', west: str = '-123.50', south: str = '48.35', east: str = '-123.20', north: str = '48.60', status: str = 'ALL', arrival_date: str = '', arrival_time: str = '', arrival_timezone: str = DEFAULT_ARRIVAL_TIMEZONE, search_now: str = '', services=Depends(get_services)):
    filters = {key: value for key, value in locals().items() if key not in ('request', 'services')}
    context = {**selection_context(services), 'filters': filters, 'results': [], 'counts': {}, 'map_data': []}
    try:
        resolved = resolve_arrival(arrival_at, arrival_date, arrival_time, arrival_timezone, search_now)
        data = validated(SearchInput, {'driver_id': driver_id, 'vehicle_id': vehicle_id, 'arrival_at': resolved, 'bbox': {key: filters[key] for key in DEFAULT_BBOX}, 'status': status})
        result = services.search(**data)
    except AppError as exc:
        if exc.status_code != 400:
            raise
        return render(request, 'stations/list.html', {**context, 'errors': exc.field_errors or {'form': exc.message}}, 400)
    instant = result['arrival_at']
    filters['arrival_at'] = instant
    filters.update(arrival_form_values(instant, arrival_timezone))
    results = [result_context(item, data['driver_id'], data['vehicle_id'], instant, arrival_timezone) for item in result['results']]
    map_data = [{'latitude': item['station']['latitude'], 'longitude': item['station']['longitude'], 'name': item['station'].get('name') or 'Unnamed station', 'status': item['overall_status'], 'url': item['detail_url']} for item in results]
    return render(request, 'stations/list.html', {**context, **result, 'filters': filters, 'results': results, 'map_data': map_data,
        'arrival_timezone': arrival_timezone, 'selected_driver': services.get_driver(data['driver_id']), 'selected_vehicle': services.get_vehicle(data['vehicle_id'])})


@router.get('/stations/{station_id}')
def detail(station_id: int, request: Request, driver_id: str = '', vehicle_id: str = '', arrival_at: str = '', arrival_timezone: str = DEFAULT_ARRIVAL_TIMEZONE, services=Depends(get_services)):
    resolve_arrival(arrival_timezone=arrival_timezone)
    data = validated(EvaluationInput, {'driver_id': driver_id, 'vehicle_id': vehicle_id, 'arrival_at': arrival_at})
    result = services.detail(station_id, **data)
    context = result_context(result, data['driver_id'], data['vehicle_id'], result['arrival_at'], arrival_timezone)
    from urllib.parse import urlencode
    context['back_url'] = '/stations?' + urlencode({'driver_id': data['driver_id'], 'vehicle_id': data['vehicle_id'], 'arrival_at': result['arrival_at'], 'arrival_timezone': arrival_timezone})
    context['selected_driver'] = services.get_driver(data['driver_id'])
    context['selected_vehicle'] = services.get_vehicle(data['vehicle_id'])
    return render(request, 'stations/detail.html', context)
