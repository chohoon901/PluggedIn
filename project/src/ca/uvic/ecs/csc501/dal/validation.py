from sqlalchemy import select
from .models import *
from .metadata import read_metadata, normalize_stations


def aggregate_issues(session, settings, metadata=None):
    """Deferred total-ISA and aggregate cardinalities, after all writes flush."""
    issues = []
    roles = set(session.scalars(select(SiteOwnerModel.organization_id))) | set(session.scalars(select(OperatorModel.organization_id))) | set(session.scalars(select(NetworkModel.organization_id)))
    for identifier in session.scalars(select(OrganizationModel.organization_id)):
        if identifier not in roles:
            issues.append(f'organization {identifier}: at least one role is required')
    for model, column in ((SiteOwnerModel, StationModel.owner_id), (OperatorModel, StationModel.operator_id)):
        station_roles = set(session.scalars(select(column)))
        for identifier in session.scalars(select(model.organization_id)):
            if identifier not in station_roles:
                issues.append(f'{model.__tablename__} {identifier}: at least one station is required')
    accepted = set(session.scalars(select(VehicleAcceptsModel.vehicle_id)))
    for identifier in session.scalars(select(VehicleModel.vehicle_id)):
        if identifier not in accepted:
            issues.append(f'vehicle {identifier}: at least one accepted connector is required')
    metadata = read_metadata(settings) if metadata is None else normalize_stations(metadata)
    ports = set(session.scalars(select(PortModel.station_id)))
    periods = set(session.scalars(select(OperatingPeriodModel.station_id)))
    for identifier in session.scalars(select(StationModel.station_id)):
        if metadata.get(str(identifier), {}).get('aggregateCompleteness') == 'INCOMPLETE':
            continue
        if identifier not in ports:
            issues.append(f'station {identifier}: at least one port or explicit INCOMPLETE metadata is required')
        if identifier not in periods:
            issues.append(f'station {identifier}: operating periods or explicit INCOMPLETE metadata are required')
    return issues
