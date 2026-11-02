"""Explicit initialization: an existing database is inspected, never replaced."""
import sqlite3
from ca.uvic.ecs.csc501.cmn.contracts.errors import NotReadyError
from ..database import Database
from .validate_db import SCHEMA_PATH, validate_schema


def init_database(database: Database | None = None) -> None:
    database = database or Database()
    path = database.settings.database_path
    if path.exists():
        issues = validate_schema(database)
        if issues:
            raise NotReadyError('; '.join(issues))
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive file creation prevents an initialization race from replacing data.
        with path.open('xb'):
            pass
        with sqlite3.connect(path) as connection:
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute(f'PRAGMA busy_timeout={database.settings.busy_timeout_ms}')
            connection.executescript('BEGIN;\n' + SCHEMA_PATH.read_text(encoding='utf-8') + '\nCOMMIT;')
    except (OSError, sqlite3.Error) as error:
        raise NotReadyError('Database initialization failed: ' + str(error)) from error


if __name__ == '__main__':
    init_database()
    print('Database initialized or existing schema verified.')
