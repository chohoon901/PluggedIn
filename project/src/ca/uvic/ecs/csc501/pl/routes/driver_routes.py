from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from ..dependencies import get_services
from ..schemas import DriverInput
from ..views import form_page, render, save_form

router = APIRouter()


@router.get('/drivers')
def drivers(request: Request, services=Depends(get_services)):
    return render(request, 'drivers/list.html', {'items': services.list_drivers()})


@router.get('/drivers/new')
def new_driver(request: Request, services=Depends(get_services)):
    return form_page(request, services, 'drivers')


@router.post('/drivers')
def create_driver(request: Request, licence_number: str = Form(''), name: str = Form(''), carrier_name: str = Form(''), services=Depends(get_services)):
    return save_form(request, services, 'drivers', DriverInput, {'licence_number': licence_number, 'name': name, 'carrier_name': carrier_name})


@router.get('/drivers/{driver_id}/edit')
def edit_driver(driver_id: int, request: Request, services=Depends(get_services)):
    return form_page(request, services, 'drivers', services.get_driver(driver_id), item_id=driver_id)


@router.post('/drivers/{driver_id}')
def update_driver(driver_id: int, request: Request, licence_number: str = Form(''), name: str = Form(''), carrier_name: str = Form(''), services=Depends(get_services)):
    return save_form(request, services, 'drivers', DriverInput, {'licence_number': licence_number, 'name': name, 'carrier_name': carrier_name}, driver_id)


@router.post('/drivers/{driver_id}/delete')
def delete_driver(driver_id: int, services=Depends(get_services)):
    services.delete_driver(driver_id)
    return RedirectResponse('/drivers', status_code=303)
