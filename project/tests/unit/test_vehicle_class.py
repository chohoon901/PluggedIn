from dataclasses import replace
from decimal import Decimal
from importlib import import_module

import pytest


@pytest.mark.parametrize('raw,expected', [('LD','LD'),(' md ','MD'),('hd','HD'),
    ('CAR','LD'),('MEDIUM_TRUCK','MD'),('HEAVY_TRUCK','HD'),
    ('VAN','UNKNOWN'),('ALL','UNKNOWN'),('', 'UNKNOWN'),(None,'UNKNOWN'),('BUS','UNKNOWN')])
def test_nlr_vehicle_class_classifies_without_rewriting(raw, expected):
    cls = import_module('ca.uvic.ecs.csc501.cmn.enums.vehicle_class').VehicleClass
    assert cls.from_name(raw).value == expected


@pytest.mark.parametrize('vehicle,maximum,expected', [
    ('CAR','LD','PASS'), ('LD','LD','PASS'), ('LD','MD','PASS'), ('LD','HD','PASS'),
    ('MD','LD','FAIL'), ('HD','MD','FAIL'),
    ('MD','MD','UNKNOWN'), ('HD','HD','UNKNOWN'),
    ('LD',None,'UNKNOWN'), (None,'LD','UNKNOWN'), ('VAN','LD','UNKNOWN')])
def test_nlr_access_and_truck_clearance(vehicle, maximum, expected):
    base = 'ca.uvic.ecs.csc501.cmn.'
    Station = import_module(base+'domain.station').Station
    Vehicle = import_module(base+'domain.vehicle').Vehicle
    models = import_module(base+'contracts.models')
    check = import_module(base+'services.evaluation').check_access
    entity = Station(1, Decimal('49.2'), Decimal('-123.1'), None,None,None,'BC',
                     'ACTIVE','public',False,maximum,True,None,None,None)
    snapshot = models.StationSnapshot(entity,(),(),(),(),models.StationMetadata())
    selected = models.VehicleSnapshot(Vehicle(1,'x'*17,vehicle_class=vehicle),())
    assert check(snapshot, selected).status == expected
    assert entity.max_vehicle_class == maximum
    assert selected.vehicle.vehicle_class == vehicle
    if vehicle in ('MD','HD') and expected == 'UNKNOWN':
        assert any(r.code == 'TRUCK_CLEARANCE_UNKNOWN' for r in check(snapshot,selected).reasons)


def test_all_entities_and_enums_live_in_the_requested_packages():
    base = 'ca.uvic.ecs.csc501.cmn.'
    for name in ('organization','site_owner','operator','network','station','connector_type',
                 'port','operating_period','adapter','vehicle','vehicle_accepts','driver','membership'):
        assert import_module(base+'domain.'+name)
    assert import_module(base+'enums.connector_family').ConnectorFamily.from_name('J1772COMBO').value == 'CCS1'
    assert import_module(base+'enums.evaluation').CheckStatus.PASS.value == 'PASS'
