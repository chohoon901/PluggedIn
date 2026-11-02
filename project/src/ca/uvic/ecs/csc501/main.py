"""저장 구현과 순수 use case, HTTP 화면을 연결하는 애플리케이션 조립점."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .cmn.application.services import ApplicationService
from .dal.database import Database
from .dal.unit_of_work import SqlAlchemyUnitOfWork
from .pl.error_handlers import register_error_handlers
from .pl.routes import router


def create_app(database: Database | None = None) -> FastAPI:
    owned = database is None
    database = database or Database()

    @asynccontextmanager
    async def lifespan(app):
        yield
        if owned:
            database.engine.dispose()

    app = FastAPI(title="PluggedIn", version="0.1.0", lifespan=lifespan)
    app.state.services = ApplicationService(lambda: SqlAlchemyUnitOfWork(database), database.health)
    register_error_handlers(app)
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "pl" / "static"), name="static")
    return app


app = create_app()
