"""저장 구현과 순수 use case, HTTP 화면을 연결하는 애플리케이션 조립점."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .cmn.application.semantic import SemanticService
from .cmn.application.services import ApplicationService
from .cmn.contracts.semantic import SemanticRepository
from .dal.semantic.repository import VirtuosoSemanticRepository
from .dal.semantic.store import VirtuosoStore
from .dal.semantic.unit_of_work import VirtuosoUnitOfWork
from .dal.settings import Settings
from .pl.error_handlers import register_error_handlers
from .pl.routes import router


def create_app(
    *, services: ApplicationService | None = None, semantic_repository: SemanticRepository | None = None,
) -> FastAPI:
    if services is None or semantic_repository is None:
        settings = Settings()
        store = VirtuosoStore.from_settings(settings)
        if services is None:
            services = ApplicationService(lambda: VirtuosoUnitOfWork(store), store.health)
        if semantic_repository is None:
            semantic_repository = VirtuosoSemanticRepository(
                settings.app_sparql_endpoint, store.graph, client=store.client, require_ready=store.require_ready,
            )

    app = FastAPI(title="PluggedIn", version="0.1.0")
    app.state.services = services
    app.state.semantic_service = SemanticService(semantic_repository)
    register_error_handlers(app)
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "pl" / "static"), name="static")
    return app


app = create_app()
