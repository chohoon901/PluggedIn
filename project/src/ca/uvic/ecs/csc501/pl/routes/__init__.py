from fastapi import APIRouter
from . import pages, driver_routes, vehicle_routes, membership_routes, station_routes, api_routes

router = APIRouter()
for module in (pages, driver_routes, vehicle_routes, membership_routes, station_routes, api_routes):
    router.include_router(module.router)
