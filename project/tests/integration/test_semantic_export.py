from hashlib import sha256
from xml.etree import ElementTree

import pytest

from ca.uvic.ecs.csc501.dal.scripts.import_sample import build_sample
from ca.uvic.ecs.csc501.dal.settings import Settings


RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
XSD = 'http://www.w3.org/2001/XMLSchema#'
PLUG = 'https://github.com/chohoon901/PluggedIn/ontology/'
MIGRATION = 'https://github.com/chohoon901/PluggedIn/migration/'
DATA = 'https://github.com/chohoon901/PluggedIn/data/sample20/'
NS = {'rdf': RDF, 'plug': PLUG, 'migration': MIGRATION}
RESOURCE = f'{{{RDF}}}resource'
DATATYPE = f'{{{RDF}}}datatype'


def test_export_preserves_sample_relationships_and_unknown_evidence(tmp_path, sample_sources):
    from ca.uvic.ecs.csc501.dal.scripts.export_rdf import export_rdf

    sample_root = tmp_path / 'sample20'
    build_sample(sample_root, *sample_sources)
    settings = Settings(sample_root)
    source_paths = (settings.database_path, settings.metadata_path)
    before = [sha256(path.read_bytes()).digest() for path in source_paths]
    output = tmp_path / 'sample20.rdf'

    assert export_rdf(settings, output, dataset='sample20') == {
        'adapter': 0, 'connector_type': 9, 'driver': 2, 'membership': 6,
        'network': 6, 'operating_period': 98, 'operator': 6, 'organization': 12,
        'port': 26, 'site_owner': 0, 'station': 20, 'vehicle': 4, 'vehicle_accepts': 4,
    }
    graph = ElementTree.parse(output).getroot()
    descriptions = {
        node.attrib[f'{{{RDF}}}about']: node
        for node in graph.findall('rdf:Description', NS)
    }

    station = descriptions[DATA + 'Station/1']
    assert station.find('rdf:type', NS).attrib[RESOURCE] == PLUG + 'Station'
    assert station.find('plug:operatedBy', NS).attrib[RESOURCE] == DATA + 'Organization/2'
    assert station.find('plug:ownedBy', NS) is None
    assert any(port.attrib[RESOURCE] == DATA + 'Port/1' for port in station.findall('plug:hasPort', NS))
    operator = descriptions[DATA + 'Organization/2']
    assert {role.attrib[RESOURCE] for role in operator.findall('rdf:type', NS)} == {
        PLUG + 'Organization', PLUG + 'Operator',
    }
    assert station.findtext('migration:portsCompleteness', namespaces=NS) == 'PARTIAL'
    assert {field.text for field in station.findall('migration:unconfirmedField', NS)} == {
        'accepts_guest_payment', 'has_truck_parking', 'quantity', 'power_kw',
    }
    assert station.find('plug:acceptsGuestPayment', NS) is None
    assert station.find('plug:hasTruckParking', NS) is None
    recorded_payment = station.find('migration:recordedAcceptsGuestPayment', NS)
    assert recorded_payment.attrib[DATATYPE] == XSD + 'boolean'
    assert recorded_payment.text in {'false', '0'}

    port = descriptions[DATA + 'Port/1']
    assert port.find('plug:hasConnectorType', NS).attrib[RESOURCE] == DATA + 'ConnectorType/4'
    assert port.find('plug:powerKw', NS) is None
    assert port.find('plug:quantity', NS) is None
    assert port.findtext('migration:recordedQuantity', namespaces=NS) == '6'

    for identifier, source_name, expected_family in (
        (2, 'J1772COMBO', 'CCS1'),
        (5, 'CCS (Type 1)', 'CCS1'),
        (4, 'Tesla (Model S/X)', 'NACS'),
    ):
        connector = descriptions[DATA + f'ConnectorType/{identifier}']
        assert connector.findtext('plug:connectorName', namespaces=NS) == source_name
        assert [
            (family.text, family.attrib[DATATYPE])
            for family in connector.findall('migration:connectorFamily', NS)
        ] == [(expected_family, XSD + 'string')]

    vehicle = descriptions[DATA + 'Vehicle/1']
    assert vehicle.find('plug:vehicleAccepts', NS).attrib[RESOURCE] == DATA + 'ConnectorType/2'
    acceptance = descriptions[DATA + 'VehicleAcceptance/1']
    assert acceptance.find('rdf:type', NS).attrib[RESOURCE] == MIGRATION + 'VehicleAcceptance'
    assert acceptance.find('migration:acceptingVehicle', NS).attrib[RESOURCE] == DATA + 'Vehicle/1'
    assert acceptance.find('migration:acceptedConnector', NS).attrib[RESOURCE] == DATA + 'ConnectorType/2'

    exported = output.read_bytes()
    with pytest.raises(FileExistsError):
        export_rdf(settings, output, dataset='sample20')
    assert output.read_bytes() == exported
    assert [sha256(path.read_bytes()).digest() for path in source_paths] == before
