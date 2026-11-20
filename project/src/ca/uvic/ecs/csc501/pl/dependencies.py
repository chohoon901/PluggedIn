from typing import TYPE_CHECKING
from fastapi import Request

if TYPE_CHECKING:
    from ca.uvic.ecs.csc501.cmn.application.semantic import SemanticService
    from ca.uvic.ecs.csc501.cmn.application.services import ApplicationService


def get_services(request: Request) -> 'ApplicationService':
    return request.app.state.services


def get_semantic_service(request: Request) -> 'SemanticService':
    return request.app.state.semantic_service
