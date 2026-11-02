from typing import TYPE_CHECKING
from fastapi import Request

if TYPE_CHECKING:
    from ca.uvic.ecs.csc501.cmn.application.services import ApplicationService


def get_services(request: Request) -> 'ApplicationService':
    return request.app.state.services
