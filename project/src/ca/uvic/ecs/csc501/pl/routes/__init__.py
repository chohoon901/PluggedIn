from fastapi import APIRouter
from . import api_routes, driver_routes, membership_routes, pages, semantic_routes, station_routes, vehicle_routes

router = APIRouter()
for module in (pages, driver_routes, vehicle_routes, membership_routes, station_routes, semantic_routes, api_routes):
    router.include_router(module.router)
