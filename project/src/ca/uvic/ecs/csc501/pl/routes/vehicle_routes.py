from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from ..dependencies import get_services
from ..schemas import VehicleInput
from ..views import form_page, render, save_form

router = APIRouter()


@router.get('/vehicles')
def vehicles(request: Request, services=Depends(get_services)):
    return render(request, 'vehicles/list.html', {'items': services.list_vehicles(), 'connectors': services.catalog()['connectors']})


@router.get('/vehicles/new')
def new_vehicle(request: Request, services=Depends(get_services)):
    return form_page(request, services, 'vehicles')


@router.post('/vehicles')
def create_vehicle(request: Request, vin: str = Form(''), licence_plate: str = Form(''), make: str = Form(''), model: str = Form(''), vehicle_class: str = Form(''), range_km: str = Form(''), max_charge_kw: str = Form(''), accepted_connector_ids: list[str] = Form([]), services=Depends(get_services)):
    values = {key: value for key, value in locals().items() if key not in ('request', 'services')}
    return save_form(request, services, 'vehicles', VehicleInput, values)


@router.get('/vehicles/{vehicle_id}/edit')
def edit_vehicle(vehicle_id: int, request: Request, services=Depends(get_services)):
    return form_page(request, services, 'vehicles', services.get_vehicle(vehicle_id), item_id=vehicle_id)


@router.post('/vehicles/{vehicle_id}')
def update_vehicle(vehicle_id: int, request: Request, vin: str = Form(''), licence_plate: str = Form(''), make: str = Form(''), model: str = Form(''), vehicle_class: str = Form(''), range_km: str = Form(''), max_charge_kw: str = Form(''), accepted_connector_ids: list[str] = Form([]), services=Depends(get_services)):
    values = {key: value for key, value in locals().items() if key not in ('request', 'services', 'vehicle_id')}
    return save_form(request, services, 'vehicles', VehicleInput, values, vehicle_id)


@router.post('/vehicles/{vehicle_id}/delete')
def delete_vehicle(vehicle_id: int, services=Depends(get_services)):
    services.delete_vehicle(vehicle_id)
    return RedirectResponse('/vehicles', status_code=303)
