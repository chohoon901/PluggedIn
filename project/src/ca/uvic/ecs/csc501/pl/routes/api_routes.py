from fastapi import APIRouter, Depends, Response
from ca.uvic.ecs.csc501.cmn.contracts.errors import NotReadyError
from ..dependencies import get_services
from ..schemas import DriverInput, VehicleInput, MembershipInput, SearchInput, EvaluationInput

router = APIRouter(prefix='/api/v1')


@router.get('/health')
def health(services=Depends(get_services)):
    if not services.health():
        raise NotReadyError('Initialize the database and prepare the demo data first.')
    return {'status': 'ok'}


@router.get('/catalog')
def catalog(services=Depends(get_services)):
    return services.catalog()


@router.get('/drivers')
def drivers(services=Depends(get_services)):
    return services.list_drivers()


@router.post('/drivers', status_code=201)
def create_driver(data: DriverInput, services=Depends(get_services)):
    return services.save_driver(data.model_dump(mode='json'))


@router.get('/drivers/{driver_id}')
def driver(driver_id: int, services=Depends(get_services)):
    return services.get_driver(driver_id)


@router.put('/drivers/{driver_id}')
def update_driver(driver_id: int, data: DriverInput, services=Depends(get_services)):
    return services.save_driver(data.model_dump(mode='json'), driver_id)


@router.delete('/drivers/{driver_id}', status_code=204)
def delete_driver(driver_id: int, services=Depends(get_services)):
    services.delete_driver(driver_id)
    return Response(status_code=204)


@router.get('/vehicles')
def vehicles(services=Depends(get_services)):
    return services.list_vehicles()


@router.post('/vehicles', status_code=201)
def create_vehicle(data: VehicleInput, services=Depends(get_services)):
    return services.save_vehicle(data.model_dump(mode='json'))


@router.get('/vehicles/{vehicle_id}')
def vehicle(vehicle_id: int, services=Depends(get_services)):
    return services.get_vehicle(vehicle_id)


@router.put('/vehicles/{vehicle_id}')
def update_vehicle(vehicle_id: int, data: VehicleInput, services=Depends(get_services)):
    return services.save_vehicle(data.model_dump(mode='json'), vehicle_id)


@router.delete('/vehicles/{vehicle_id}', status_code=204)
def delete_vehicle(vehicle_id: int, services=Depends(get_services)):
    services.delete_vehicle(vehicle_id)
    return Response(status_code=204)


@router.get('/memberships')
def memberships(driver_id: int | None = None, services=Depends(get_services)):
    return services.list_memberships(driver_id)


@router.post('/memberships', status_code=201)
def create_membership(data: MembershipInput, services=Depends(get_services)):
    return services.save_membership(data.model_dump(mode='json'))


@router.get('/memberships/{membership_id}')
def membership(membership_id: int, services=Depends(get_services)):
    return services.get_membership(membership_id)


@router.put('/memberships/{membership_id}')
def update_membership(membership_id: int, data: MembershipInput, services=Depends(get_services)):
    return services.save_membership(data.model_dump(mode='json'), membership_id)


@router.delete('/memberships/{membership_id}', status_code=204)
def delete_membership(membership_id: int, services=Depends(get_services)):
    services.delete_membership(membership_id)
    return Response(status_code=204)


@router.post('/stations/search')
def search(data: SearchInput, services=Depends(get_services)):
    return services.search(**data.model_dump(mode='json'))


@router.post('/stations/{station_id}/evaluate')
def evaluate(station_id: int, data: EvaluationInput, services=Depends(get_services)):
    return services.detail(station_id, **data.model_dump(mode='json'))
