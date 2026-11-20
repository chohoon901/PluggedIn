"""저장 구현과 순수 use case, HTTP 화면을 연결하는 애플리케이션 조립점."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .cmn.application.semantic import SemanticService
from .cmn.application.services import ApplicationService
from .cmn.contracts.semantic import SemanticRepository
from .dal.database import Database
from .dal.semantic.repository import VirtuosoSemanticRepository
from .dal.unit_of_work import SqlAlchemyUnitOfWork
from .pl.error_handlers import register_error_handlers
from .pl.routes import router


def create_app(
    database: Database | None = None, *, semantic_repository: SemanticRepository | None = None,
) -> FastAPI:
    owned = database is None
    database = database or Database()
    if semantic_repository is None:
        settings = database.settings
        semantic_repository = VirtuosoSemanticRepository(settings.sparql_endpoint, settings.sparql_graph)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if owned:
            database.engine.dispose()

    app = FastAPI(title="PluggedIn", version="0.1.0", lifespan=lifespan)
    app.state.services = ApplicationService(lambda: SqlAlchemyUnitOfWork(database), database.health)
    app.state.semantic_service = SemanticService(semantic_repository)
    register_error_handlers(app)
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "pl" / "static"), name="static")
    return app


app = create_app()
