"""Explicit, backed-up ORM data migration to the project's NLR class policy."""
import argparse
from pathlib import Path
import sqlite3

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from ..models import VehicleModel, StationModel


# 사용자 요청에 따른 기존 프로젝트 값의 변환 정책입니다. 실제 모든 밴의 법정 등급을 뜻하지 않습니다.
_LEGACY = {'CAR': 'LD', 'VAN': 'MD', 'MEDIUM_TRUCK': 'MD', 'HEAVY_TRUCK': 'HD'}


def _canonical(value):
    if value is None:
        return None
    normalized = ' '.join(value.upper().split())
    return _LEGACY.get(normalized, normalized) if normalized in (*_LEGACY, 'LD', 'MD', 'HD') else value


def _issues(connection):
    return (list(connection.exec_driver_sql('PRAGMA foreign_key_check')) +
            [row for row in connection.exec_driver_sql('PRAGMA integrity_check') if row[0] != 'ok'])


def migrate_vehicle_classes(database_path: Path, backup_path: Path) -> dict:
    """Change only the two class columns; works with original and nullable-role schemas.

    Stop the app before calling. Missing files are never created, backups never
    overwritten, and rerunning an already canonical database is a no-op.
    """
    database_path, backup_path = database_path.resolve(), backup_path.resolve()
    if not database_path.is_file():
        raise FileNotFoundError(database_path)
    if database_path == backup_path:
        raise ValueError('The backup must be a different file.')
    engine = create_engine('sqlite:///' + database_path.as_posix())

    @event.listens_for(engine, 'connect')
    def configure(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=5000')

    try:
        with Session(engine) as session, session.begin():
            if _issues(session.connection()):
                raise ValueError('Existing database integrity checks failed; no values changed.')
            pending = []
            counts = {'vehicle': 0, 'station': 0}
            for model, field, label in ((VehicleModel, 'vehicle_class', 'vehicle'),
                                        (StationModel, 'max_vehicle_class', 'station')):
                for row in session.scalars(select(model)):
                    old = getattr(row, field)
                    new = _canonical(old)
                    if old != new:
                        pending.append((row, field, new))
                        counts[label] += 1
            if not pending:
                return counts
            if backup_path.exists():
                raise FileExistsError(f'Backup already exists: {backup_path}')
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(database_path.as_uri() + '?mode=ro', uri=True) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            for row, field, new in pending:
                setattr(row, field, new)
            session.flush()
            if _issues(session.connection()):
                raise ValueError('Migration integrity checks failed; changes rolled back.')
            return counts
    finally:
        engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    print(migrate_vehicle_classes(args.database, args.backup))
