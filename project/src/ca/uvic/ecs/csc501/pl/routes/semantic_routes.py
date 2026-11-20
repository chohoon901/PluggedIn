"""Read-only SSR pages backed by the charging knowledge graph."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ca.uvic.ecs.csc501.cmn.application.semantic import SemanticService
from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError
from ..dependencies import get_semantic_service
from ..views import render


router = APIRouter()


@router.get('/semantic', include_in_schema=False)
def semantic_queries(request: Request, vehicle_iri: str | None = None):
    if vehicle_iri is None:
        return RedirectResponse(request.url_for('fast_charging'))
    return RedirectResponse(request.url_for('adapter_finder').include_query_params(vehicle_iri=vehicle_iri))


@router.get('/fast-charging')
def fast_charging(
    request: Request,
    min_power_kw: str | None = None,
    service: SemanticService = Depends(get_semantic_service),
):
    context = {'min_power_kw': min_power_kw, 'fast_chargers': None}
    if min_power_kw is not None:
        try:
            context['fast_chargers'] = service.fast_chargers(min_power_kw)
        except InputError as error:
            context['power_error'] = error.field_errors.get('min_power_kw', error.message)
            return render(request, 'semantic/fast_charging.html', context, status_code=400)
    return render(request, 'semantic/fast_charging.html', context)


@router.get('/adapter-finder')
def adapter_finder(
    request: Request,
    vehicle_iri: str | None = None,
    service: SemanticService = Depends(get_semantic_service),
):
    vehicles = service.vehicles()
    context = {
        'vehicles': vehicles,
        'vehicle_iri': vehicle_iri,
        'adapter_candidates': None,
    }
    if vehicle_iri is not None:
        try:
            context['adapter_candidates'] = service.adapter_candidates(vehicle_iri, vehicles)
        except InputError as error:
            context['vehicle_error'] = error.field_errors.get('vehicle_iri', error.message)
            return render(request, 'semantic/adapter_finder.html', context, status_code=400)
    return render(request, 'semantic/adapter_finder.html', context)
