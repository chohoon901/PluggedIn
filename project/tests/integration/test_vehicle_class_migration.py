import sqlite3
import pytest

from sqlalchemy import select

from ca.uvic.ecs.csc501.dal.database import Database
from ca.uvic.ecs.csc501.dal.settings import Settings
from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
from ca.uvic.ecs.csc501.dal.models import VehicleModel, StationModel


def test_class_migration_preserves_backup_schema_and_other_fields(tmp_path):
    from ca.uvic.ecs.csc501.dal.scripts.migrate_vehicle_classes import migrate_vehicle_classes
    db = Database(Settings(tmp_path / 'dal'))
    init_database(db)
    seed_demo(db)
    with db.session_factory() as session:
        session.get(VehicleModel, 1).vehicle_class = 'CAR'
        session.get(StationModel, 1).max_vehicle_class = 'VAN'
        session.get(StationModel, 2).max_vehicle_class = 'MEDIUM_TRUCK'
        session.get(StationModel, 3).max_vehicle_class = 'HEAVY_TRUCK'
        session.get(StationModel, 4).max_vehicle_class = 'CAR'
        session.get(StationModel, 5).max_vehicle_class = None
        session.commit()
    path = db.settings.database_path
    before = path.read_bytes()
    with sqlite3.connect(path) as con:
        original_schema = con.execute('SELECT sql FROM sqlite_master ORDER BY name').fetchall()
        old_vehicles = con.execute('SELECT vehicle_id,vin,model FROM vehicle').fetchall()
    backup = tmp_path / 'backup.sqlite-backup'
    assert migrate_vehicle_classes(path, backup) == {'vehicle': 1, 'station': 4}
    with sqlite3.connect(backup) as con:
        assert con.execute('SELECT class FROM vehicle').fetchone()[0] == 'CAR'
        assert con.execute('SELECT max_vehicle_class FROM station WHERE station_id=1').fetchone()[0] == 'VAN'
    with db.session_factory() as session:
        assert session.get(VehicleModel, 1).vehicle_class == 'LD'
        assert list(session.scalars(select(StationModel.max_vehicle_class).order_by(StationModel.station_id))) == ['MD','MD','HD','LD',None]
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT sql FROM sqlite_master ORDER BY name').fetchall() == original_schema
        assert con.execute('SELECT vehicle_id,vin,model FROM vehicle').fetchall() == old_vehicles
    after = path.read_bytes()
    assert migrate_vehicle_classes(path, backup) == {'vehicle': 0, 'station': 0}
    assert path.read_bytes() == after
    db.engine.dispose()


def test_existing_backup_refuses_to_overwrite_or_change_database(tmp_path):
    from ca.uvic.ecs.csc501.dal.scripts.migrate_vehicle_classes import migrate_vehicle_classes
    db = Database(Settings(tmp_path / 'dal'))
    init_database(db)
    seed_demo(db)
    with db.session_factory() as session:
        session.get(VehicleModel, 1).vehicle_class = 'VAN'
        session.commit()
    path = db.settings.database_path
    before = path.read_bytes()
    backup = tmp_path / 'existing.sqlite-backup'
    backup.write_bytes(b'keep existing backup')
    with pytest.raises(FileExistsError):
        migrate_vehicle_classes(path, backup)
    assert path.read_bytes() == before
    assert backup.read_bytes() == b'keep existing backup'
    db.engine.dispose()
