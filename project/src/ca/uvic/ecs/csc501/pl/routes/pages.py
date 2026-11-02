from fastapi import APIRouter, Depends, Request
from ..dependencies import get_services
from ..views import DEFAULT_BBOX, now_string, render, selection_context
from ..arrival import arrival_form_values

router = APIRouter()


@router.get('/')
def index(request: Request, services=Depends(get_services)):
    return render(request, 'index.html', {**selection_context(services), 'filters': {**DEFAULT_BBOX, **arrival_form_values(now_string()), 'status': 'ALL'}})
