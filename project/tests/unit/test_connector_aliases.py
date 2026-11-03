from dataclasses import replace
from decimal import Decimal

import pytest

from ca.uvic.ecs.csc501.cmn.domain.station import Station
from ca.uvic.ecs.csc501.cmn.domain.connector_type import ConnectorType
from ca.uvic.ecs.csc501.cmn.domain.port import Port
from ca.uvic.ecs.csc501.cmn.contracts.models import StationSnapshot, StationMetadata, VehicleSnapshot
from ca.uvic.ecs.csc501.cmn.domain.vehicle import Vehicle
from ca.uvic.ecs.csc501.cmn.services.evaluation import check_connector


def test_unknown_station_roles_are_valid_but_invalid_nonnull_ids_are_not():
    station = Station(1, Decimal('49.2'), Decimal('-123.1'), 'Source station', None,
                      'Vancouver', 'BC', 'ACTIVE', 'public', False, None, False, None, None, None)
    assert station.owner_id is None and station.operator_id is None
    with pytest.raises(ValueError):
        replace(station, owner_id=0)


@pytest.mark.parametrize('source,accepted,current,expected', [
    ('CCS (Type 1)', 'J1772COMBO', 'DC', 'PASS'),
    ('J1772COMBO', 'CCS1', 'DC', 'PASS'),
    ('Type 1 (J1772)', 'J1772', 'AC', 'PASS'),
    ('CHAdeMO', 'CHADEMO', 'DC', 'PASS'),
    ('CCS (Type 1)', 'CCS1', 'AC', 'UNKNOWN'),
    ('NACS / Tesla Supercharger', 'TESLA', 'DC', 'UNKNOWN'),
    ('NEMA 5-20R', 'NEMA520', 'AC', 'UNKNOWN'),
    ('CCS (Type 1)', 'CHADEMO', 'DC', 'FAIL'),
    ('CCS (Type 2)', 'J1772COMBO', 'DC', 'FAIL'),
    ('Unrecognized A', 'Unrecognized B', 'DC', 'UNKNOWN'),
])
def test_source_aliases_match_across_distinct_database_ids(source, accepted, current, expected):
    from ca.uvic.ecs.csc501.cmn.enums.connector_family import ConnectorFamily
    assert ConnectorFamily.from_name(source) is not None
    station = StationSnapshot(None, (), (), (ConnectorType(10, source),), (), StationMetadata())
    vehicle = VehicleSnapshot(Vehicle(1, 'x'*17), (20,), (accepted,))
    assert check_connector(station, vehicle, Port(1, 1, 1, 10, None, current, 1)).status == expected
