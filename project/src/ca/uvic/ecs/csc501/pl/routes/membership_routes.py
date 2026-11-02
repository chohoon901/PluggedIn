from fastapi import APIRouter, Depends, Form, Request
from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError
from fastapi.responses import RedirectResponse
from ..dependencies import get_services
from ..schemas import MembershipInput
from ..views import form_page, render, save_form

router = APIRouter()


@router.get('/memberships')
def memberships(request: Request, driver_id: str = '', services=Depends(get_services)):
    try:
        selected = int(driver_id) if driver_id.strip() else None
        if selected is not None and selected <= 0:
            raise ValueError
    except ValueError as exc:
        raise InputError('Choose a valid driver.', {'driver_id': 'Driver IDs must be positive integers.'}) from exc
    return render(request, 'memberships/list.html', {'items': services.list_memberships(selected), 'drivers': services.list_drivers(), 'networks': services.catalog()['networks'], 'selected_driver_id': selected})


@router.get('/memberships/new')
def new_membership(request: Request, driver_id: int | None = None, services=Depends(get_services)):
    return form_page(request, services, 'memberships', {'driver_id': driver_id})


@router.post('/memberships')
def create_membership(request: Request, driver_id: str = Form(''), network_id: str = Form(''), start_date: str = Form(''), end_date: str = Form(''), services=Depends(get_services)):
    return save_form(request, services, 'memberships', MembershipInput, {'driver_id': driver_id, 'network_id': network_id, 'start_date': start_date, 'end_date': end_date})


@router.get('/memberships/{membership_id}/edit')
def edit_membership(membership_id: int, request: Request, services=Depends(get_services)):
    return form_page(request, services, 'memberships', services.get_membership(membership_id), item_id=membership_id)


@router.post('/memberships/{membership_id}')
def update_membership(membership_id: int, request: Request, driver_id: str = Form(''), network_id: str = Form(''), start_date: str = Form(''), end_date: str = Form(''), services=Depends(get_services)):
    return save_form(request, services, 'memberships', MembershipInput, {'driver_id': driver_id, 'network_id': network_id, 'start_date': start_date, 'end_date': end_date}, membership_id)


@router.post('/memberships/{membership_id}/delete')
def delete_membership(membership_id: int, services=Depends(get_services)):
    services.delete_membership(membership_id)
    return RedirectResponse('/memberships', status_code=303)
