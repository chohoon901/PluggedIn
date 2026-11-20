"""Read-only SSR pages backed by the charging knowledge graph."""

from fastapi import APIRouter, Depends, Request

from ca.uvic.ecs.csc501.cmn.application.semantic import SemanticService
from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError
from ..dependencies import get_semantic_service
from ..views import render


router = APIRouter()


@router.get('/semantic', name='semantic_queries')
def semantic_queries(
    request: Request,
    vehicle_iri: str | None = None,
    service: SemanticService = Depends(get_semantic_service),
):
    vehicles = service.vehicles()
    context = {
        'fast_chargers': service.fast_chargers(),
        'vehicles': vehicles,
        'vehicle_iri': vehicle_iri,
        'adapter_candidates': None,
    }
    if vehicle_iri is not None:
        try:
            context['adapter_candidates'] = service.adapter_candidates(vehicle_iri, vehicles)
        except InputError as error:
            context['vehicle_error'] = error.field_errors.get('vehicle_iri', error.message)
            return render(request, 'semantic/queries.html', context, status_code=400)
    return render(request, 'semantic/queries.html', context)
