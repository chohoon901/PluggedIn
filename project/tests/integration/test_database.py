from dataclasses import replace
import json
import sqlite3

import pytest
from sqlalchemy import text

from ca.uvic.ecs.csc501.dal.settings import Settings
from ca.uvic.ecs.csc501.dal.database import Database
from ca.uvic.ecs.csc501.dal.unit_of_work import SqlAlchemyUnitOfWork
from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
from ca.uvic.ecs.csc501.dal.scripts.validate_db import validate_database
from ca.uvic.ecs.csc501.cmn.contracts.errors import ConflictError, NotReadyError


@pytest.fixture
def database(tmp_path):
    db = Database(Settings(tmp_path))
    init_database(db)
    yield db
    db.engine.dispose()


@pytest.mark.parametrize('document', [[], None])
def test_metadata_top_level_shapes_are_unknown_without_rewrite(database, document):
    seed_demo(database)
    original = json.dumps(document)
    database.settings.metadata_path.write_text(original, encoding='utf-8')
    with SqlAlchemyUnitOfWork(database) as work:
        metadata = work.stations.get(1).metadata
    assert metadata.timezone is None
    assert metadata.hours_completeness == 'UNKNOWN'
    assert database.settings.metadata_path.read_text(encoding='utf-8') == original


def test_uninitialized_database_is_not_healthy(tmp_path):
    db = Database(Settings(tmp_path))
    assert not db.health()
    with pytest.raises(NotReadyError):
        with SqlAlchemyUnitOfWork(db) as work:
            work.drivers.list()
    db.engine.dispose()


def test_schema_models_and_foreign_keys_match(database):
    from ca.uvic.ecs.csc501.dal.models import Base
    assert len(Base.metadata.tables) == 13
    assert sum(len(t.columns) for t in Base.metadata.tables.values()) == 65
    assert validate_database(database) == []
    with database.engine.connect() as a, database.engine.connect() as b:
        assert a.exec_driver_sql('PRAGMA foreign_keys').scalar() == 1
        assert b.exec_driver_sql('PRAGMA foreign_keys').scalar() == 1


def test_seed_is_idempotent_and_reads_detached_snapshots(database):
    seed_demo(database)
    seed_demo(database)
    with SqlAlchemyUnitOfWork(database) as work:
        stations = work.stations.list()
        vehicle = work.vehicles.get(1)
        assert len(work.drivers.list()) == 2
        assert len(work.memberships.list()) == 2
    assert len(stations) == 5
    assert str(stations[0].operating_periods[0].close_time) == '24:00:00'
    assert stations[3].metadata.aggregate_completeness == 'INCOMPLETE'
    assert vehicle.accepted_connector_ids == (1,)
    assert validate_database(database) == []


def test_seed_conflict_preserves_modified_data(database):
    seed_demo(database)
    with SqlAlchemyUnitOfWork(database) as work:
        work.drivers.save(replace(work.drivers.get(1), name='Changed'))
        work.commit()
    with pytest.raises(ConflictError):
        seed_demo(database)
    with SqlAlchemyUnitOfWork(database) as work:
        assert work.drivers.get(1).name == 'Changed'


def test_vehicle_replacement_is_atomic_and_unique_errors_rollback(database):
    seed_demo(database)
    with pytest.raises(ConflictError):
        with SqlAlchemyUnitOfWork(database) as work:
            original = work.vehicles.get(1).vehicle
            work.vehicles.save(replace(original, model='Changed'), [999])
            work.commit()
    with SqlAlchemyUnitOfWork(database) as work:
        assert work.vehicles.get(1).vehicle.model == 'Van'
        assert work.vehicles.get(1).accepted_connector_ids == (1,)
    with pytest.raises(ConflictError):
        with SqlAlchemyUnitOfWork(database) as work:
            work.drivers.save(replace(work.drivers.get(1), driver_id=None))
            work.commit()


def test_driver_and_vehicle_cascades_are_independent(database):
    seed_demo(database)
    with SqlAlchemyUnitOfWork(database) as work:
        work.drivers.delete(1)
        work.commit()
    with SqlAlchemyUnitOfWork(database) as work:
        assert work.memberships.list(1) == []
        assert work.vehicles.get(1) is not None
        work.vehicles.delete(1)
        work.commit()
    with SqlAlchemyUnitOfWork(database) as work:
        assert work.drivers.get(2) is not None
        assert len(work.memberships.list(2)) == 1


def test_no_roleless_organization_or_empty_vehicle_can_commit(database):
    from ca.uvic.ecs.csc501.dal.models import OrganizationModel, VehicleModel
    with pytest.raises(ConflictError):
        with SqlAlchemyUnitOfWork(database) as work:
            work.session.add(OrganizationModel(name='No role'))
            work.commit()
    with pytest.raises(ConflictError):
        with SqlAlchemyUnitOfWork(database) as work:
            work.session.add(VehicleModel(vin='OTHER000000000001'))
            work.commit()


def test_init_preserves_existing_database_and_reports_schema_damage(database):
    seed_demo(database)
    init_database(database)
    with database.engine.begin() as connection:
        connection.exec_driver_sql('DROP INDEX ix_adapter_to')
    assert any('ix_adapter_to' in issue for issue in validate_database(database))
    with pytest.raises(NotReadyError):
        init_database(database)


def test_settings_reject_paths_outside_dal(tmp_path):
    (tmp_path / 'config.properties').write_text('[sqlite]\ndatabase_path=../escape.db\n')
    with pytest.raises(ValueError):
        Settings(tmp_path)


def test_missing_metadata_is_unknown_and_does_not_fake_completeness(database):
    seed_demo(database)
    database.settings.metadata_path.unlink()
    with SqlAlchemyUnitOfWork(database) as work:
        metadata = work.stations.get(1).metadata
    assert metadata.timezone is None
    assert metadata.hours_completeness == 'UNKNOWN'
    assert metadata.ports_completeness == 'UNKNOWN'


def test_orm_preserves_named_constraints_and_all_foreign_keys(database):
    from sqlalchemy import inspect
    from ca.uvic.ecs.csc501.dal.models import Base
    inspector = inspect(database.engine)
    for table in Base.metadata.tables.values():
        assert {col['name'] for col in inspector.get_columns(table.name)} == set(table.columns.keys())
        orm_unique = {constraint.name for constraint in table.constraints if constraint.__class__.__name__ == 'UniqueConstraint'}
        assert orm_unique == {constraint['name'] for constraint in inspector.get_unique_constraints(table.name)}
        orm_named_checks = {constraint.name for constraint in table.constraints if constraint.__class__.__name__ == 'CheckConstraint' and constraint.name}
        assert orm_named_checks == {constraint['name'] for constraint in inspector.get_check_constraints(table.name) if constraint['name']}
        with database.engine.connect() as connection:
            actual_foreign_keys = connection.exec_driver_sql(f'PRAGMA foreign_key_list({table.name})').all()
        assert {(fk.parent.name, fk.target_fullname, fk.ondelete or 'NO ACTION') for fk in table.foreign_keys} == {
            (fk[3], fk[2] + '.' + fk[4], fk[6]) for fk in actual_foreign_keys
        }


@pytest.mark.parametrize('table,values', [
    ('station', {'station_id':8,'latitude':91,'longitude':0,'owner_id':1,'operator_id':1}),
    ('station', {'station_id':8,'latitude':48.46,'longitude':-123.31,'owner_id':1,'operator_id':1}),
    ('port', {'port_id':8,'station_id':1,'number':0,'connector_type_id':1}),
    ('port', {'port_id':8,'station_id':1,'number':8,'connector_type_id':1,'power_kw':-1}),
    ('port', {'port_id':8,'station_id':999,'number':8,'connector_type_id':1}),
    ('adapter', {'adapter_id':1,'model':'Invalid','from_connector_type_id':1,'to_connector_type_id':1}),
    ('operating_period', {'operating_period_id':99,'station_id':1,'day':'Mon','open_time':'24:00:00','close_time':'24:00:00'}),
    ('operating_period', {'operating_period_id':99,'station_id':1,'day':'Mon','open_time':'22:00:00','close_time':'21:00:00'}),
    ('operating_period', {'operating_period_id':99,'station_id':1,'day':'Bad','open_time':'01:00:00','close_time':'02:00:00'}),
])
def test_original_ddl_constraints_reject_invalid_orm_writes(database, table, values):
    from ca.uvic.ecs.csc501.dal.models import Base
    seed_demo(database)
    model = next(mapper.class_ for mapper in Base.registry.mappers if mapper.local_table.name == table)
    with pytest.raises(ConflictError):
        with SqlAlchemyUnitOfWork(database) as work:
            work.session.add(model(**values))
            work.commit()
    assert validate_database(database) == []


def test_validate_detects_direct_roleless_writes(database):
    from ca.uvic.ecs.csc501.dal.models import OrganizationModel
    with database.session_factory() as session:
        session.add(OrganizationModel(name='Outside UoW'))
        session.commit()
    assert any('at least one role' in issue for issue in validate_database(database))


def test_complete_station_and_owner_aggregate_rules_cannot_be_bypassed(database):
    from ca.uvic.ecs.csc501.dal.models import OperatingPeriodModel, SiteOwnerModel, OrganizationModel
    from sqlalchemy import delete
    seed_demo(database)
    with pytest.raises(ConflictError):
        with SqlAlchemyUnitOfWork(database) as work:
            work.session.execute(delete(OperatingPeriodModel).where(OperatingPeriodModel.station_id == 1))
            work.commit()
    with pytest.raises(ConflictError):
        with SqlAlchemyUnitOfWork(database) as work:
            work.session.add(OrganizationModel(organization_id=9, name='Unused owner'))
            work.session.flush()
            work.session.add(SiteOwnerModel(organization_id=9))
            work.commit()


def test_seed_detects_malformed_existing_metadata_without_overwrite(database):
    seed_demo(database)
    database.settings.metadata_path.write_text('{damaged metadata', encoding='utf-8')
    with pytest.raises(ConflictError):
        seed_demo(database)
    assert database.settings.metadata_path.read_text(encoding='utf-8') == '{damaged metadata'


def test_schema_validator_detects_changed_check_literal_case(tmp_path):
    from ca.uvic.ecs.csc501.dal.scripts.validate_db import SCHEMA_PATH
    db = Database(Settings(tmp_path))
    db.settings.database_path.parent.mkdir(parents=True)
    with sqlite3.connect(db.settings.database_path) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding='utf-8').replace("'Mon'", "'mon'"))
    assert any('operating_period' in issue for issue in validate_database(db))
    assert not db.health()
    db.engine.dispose()


@pytest.mark.parametrize('value', [[], 7, None])
def test_metadata_bad_station_entries_read_unknown_and_commit_conflicts(database, value):
    seed_demo(database)
    document = json.loads(database.settings.metadata_path.read_text(encoding='utf-8'))
    document['stations']['4'] = value
    original = json.dumps(document)
    database.settings.metadata_path.write_text(original, encoding='utf-8')
    with SqlAlchemyUnitOfWork(database) as work:
        assert work.stations.get(4).metadata.timezone is None
    assert any('station 4' in issue for issue in validate_database(database))
    with pytest.raises(ConflictError, match='station 4'):
        with SqlAlchemyUnitOfWork(database) as work:
            work.drivers.save(replace(work.drivers.get(1), name='Must rollback'))
            work.commit()
    with SqlAlchemyUnitOfWork(database) as work:
        assert work.drivers.get(1).name == 'Mina'
    assert database.settings.metadata_path.read_text(encoding='utf-8') == original


@pytest.mark.parametrize('field,value,attribute,expected', [
    ('timezone', ['America/Vancouver'], 'timezone', None),
    ('timezone', 9, 'timezone', None),
    ('timezone', 'Unknown/Invalid', 'timezone', None),
    ('hoursCompleteness', ['COMPLETE'], 'hours_completeness', 'UNKNOWN'),
    ('portsCompleteness', {}, 'ports_completeness', 'UNKNOWN'),
    ('aggregateCompleteness', ['INCOMPLETE'], 'aggregate_completeness', 'INCOMPLETE'),
    ('sourceLabel', ['source'], 'source_label', 'Unknown source'),
    ('sourceUpdatedAt', 7, 'source_updated_at', None),
])
def test_metadata_bad_field_types_use_conservative_defaults(database, field, value, attribute, expected):
    from datetime import datetime, timezone
    from ca.uvic.ecs.csc501.cmn.services.evaluation import evaluate_station
    seed_demo(database)
    document = json.loads(database.settings.metadata_path.read_text(encoding='utf-8'))
    document['stations']['1'][field] = value
    original = json.dumps(document)
    database.settings.metadata_path.write_text(original, encoding='utf-8')
    with SqlAlchemyUnitOfWork(database) as work:
        snapshot = work.stations.get(1)
        assert getattr(snapshot.metadata, attribute) == expected
        evaluate_station(snapshot, work.vehicles.get(1), work.memberships.list(1), datetime(2026,10,26,19,tzinfo=timezone.utc))
    assert database.settings.metadata_path.read_text(encoding='utf-8') == original


@pytest.mark.parametrize('value', [7, 'accepts_guest_payment', ['accepts_guest_payment', None, 9, {}]])
def test_metadata_bad_unconfirmed_fields_cannot_confirm_defaults(database, value):
    seed_demo(database)
    document = json.loads(database.settings.metadata_path.read_text(encoding='utf-8'))
    document['stations']['1']['unconfirmedFields'] = value
    original = json.dumps(document)
    database.settings.metadata_path.write_text(original, encoding='utf-8')
    with SqlAlchemyUnitOfWork(database) as work:
        metadata = work.stations.get(1).metadata
    assert all(isinstance(field, str) for field in metadata.unconfirmed_fields)
    assert {'accepts_guest_payment', 'has_truck_parking', 'quantity'} <= set(metadata.unconfirmed_fields)
    assert database.settings.metadata_path.read_text(encoding='utf-8') == original


@pytest.mark.parametrize('value', [[], 'INCOMPLETE', {'aggregateCompleteness':['INCOMPLETE']},
                                 {'aggregateCompleteness':None}])
def test_metadata_bad_incomplete_declaration_never_exempts_children(database, value):
    seed_demo(database)
    document = json.loads(database.settings.metadata_path.read_text(encoding='utf-8'))
    document['stations']['4'] = value
    original = json.dumps(document)
    database.settings.metadata_path.write_text(original, encoding='utf-8')
    assert any('station 4' in issue for issue in validate_database(database))
    with pytest.raises(ConflictError, match='station 4'):
        with SqlAlchemyUnitOfWork(database) as work:
            work.commit()
    assert database.settings.metadata_path.read_text(encoding='utf-8') == original
