"""Non-mutating exact schema and relational/aggregate integrity inspection."""
from pathlib import Path
import re
import sqlite3
from sqlalchemy.exc import SQLAlchemyError
from ..database import Database
from ..validation import aggregate_issues


SCHEMA_PATH = Path(__file__).with_name('schema.sql')


def _normalize(sql):
    # SQL keywords are case-insensitive; CHECK string literals are not. Preserve
    # quoted text exactly so a changed allowed value cannot pass inspection.
    tokens = re.findall(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|\s+|.", sql or '', re.S)
    return ''.join(token if token.startswith(("'", '"')) else token.lower()
                   for token in tokens if not token.isspace() and not token.startswith('--')).rstrip(';')


def _schema(connection):
    return {(row[0], row[1]): _normalize(row[2]) for row in connection.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND type IN ('table','index','trigger','view')")}


def validate_schema(database):
    if not database.settings.database_path.is_file():
        return ['Database file is missing']
    try:
        with sqlite3.connect(':memory:') as expected:
            expected.execute('PRAGMA foreign_keys=ON')
            expected.execute(f'PRAGMA busy_timeout={database.settings.busy_timeout_ms}')
            expected.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
            expected_schema = _schema(expected)
        # mode=ro avoids creating a missing file during validation.
        uri = database.settings.database_path.as_uri() + '?mode=ro'
        with sqlite3.connect(uri, uri=True) as actual:
            actual.execute('PRAGMA foreign_keys=ON')
            actual.execute(f'PRAGMA busy_timeout={database.settings.busy_timeout_ms}')
            actual_schema = _schema(actual)
        issues = []
        for key, definition in expected_schema.items():
            if actual_schema.get(key) != definition:
                issues.append(f'Schema mismatch: {key[0]} {key[1]}')
        for key in actual_schema.keys() - expected_schema.keys():
            issues.append(f'Unexpected schema object: {key[0]} {key[1]}')
        return issues
    except (sqlite3.Error, OSError) as error:
        return [f'Database unavailable: {error}']


def validate_database(database: Database | None = None) -> list[str]:
    database = database or Database()
    issues = validate_schema(database)
    if issues:
        return issues
    try:
        with database.engine.connect() as connection:
            issues.extend(f'Foreign key violation: {tuple(row)}' for row in connection.exec_driver_sql('PRAGMA foreign_key_check'))
            issues.extend(f'Integrity violation: {row[0]}' for row in connection.exec_driver_sql('PRAGMA integrity_check') if row[0] != 'ok')
        with database.session_factory() as session:
            issues.extend(aggregate_issues(session, database.settings))
    except SQLAlchemyError as error:
        issues.append(f'Database unavailable: {error}')
    return issues


if __name__ == '__main__':
    problems = validate_database()
    print('\n'.join(problems) if problems else 'Database schema and data are valid.')
    raise SystemExit(1 if problems else 0)
