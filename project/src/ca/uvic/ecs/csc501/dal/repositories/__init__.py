from sqlalchemy import select, delete
from ca.uvic.ecs.csc501.cmn.driver import Driver
from ca.uvic.ecs.csc501.cmn.vehicle import Vehicle
from ca.uvic.ecs.csc501.cmn.membership import Membership
from ca.uvic.ecs.csc501.cmn.organization import Organization
from ca.uvic.ecs.csc501.cmn.station import Station
from ca.uvic.ecs.csc501.cmn.port import Port
from ca.uvic.ecs.csc501.cmn.operating_period import OperatingPeriod
from ca.uvic.ecs.csc501.cmn.connector_type import ConnectorType
from ca.uvic.ecs.csc501.cmn.contracts.models import VehicleSnapshot, StationSnapshot
from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError, NotFoundError
from ..models import *
from ..mappers import to_domain, copy_to_model
from ..metadata import station_metadata


class EntityRepository:
    def __init__(self, session, model, entity, key):
        self.session, self.model, self.entity, self.key = session, model, entity, key

    def get(self, identifier):
        model = self.session.get(self.model, identifier)
        return to_domain(self.entity, model) if model else None

    def list(self):
        return [to_domain(self.entity, item) for item in self.session.scalars(select(self.model).order_by(getattr(self.model, self.key)))]

    def save(self, entity):
        identifier = getattr(entity, self.key)
        model = self.session.get(self.model, identifier) if identifier is not None else self.model()
        if model is None:
            raise NotFoundError('The registered item could not be found.')
        copy_to_model(entity, model)
        self.session.add(model)
        self.session.flush()
        return to_domain(self.entity, model)

    def delete(self, identifier):
        model = self.session.get(self.model, identifier)
        if model is not None:
            self.session.delete(model)
            self.session.flush()


class DriverRepository(EntityRepository):
    def __init__(self, session):
        super().__init__(session, DriverModel, Driver, 'driver_id')


class MembershipRepository(EntityRepository):
    def __init__(self, session):
        super().__init__(session, MembershipModel, Membership, 'membership_id')

    def list(self, driver_id=None):
        query = select(MembershipModel).order_by(MembershipModel.membership_id)
        if driver_id is not None:
            query = query.where(MembershipModel.driver_id == driver_id)
        return [to_domain(Membership, item) for item in self.session.scalars(query)]


class OrganizationRepository(EntityRepository):
    def __init__(self, session):
        super().__init__(session, OrganizationModel, Organization, 'organization_id')


class VehicleRepository(EntityRepository):
    def __init__(self, session):
        super().__init__(session, VehicleModel, Vehicle, 'vehicle_id')

    def get(self, identifier):
        vehicle = super().get(identifier)
        if vehicle is None:
            return None
        ids = tuple(self.session.scalars(select(VehicleAcceptsModel.connector_type_id)
                                        .where(VehicleAcceptsModel.vehicle_id == identifier)
                                        .order_by(VehicleAcceptsModel.connector_type_id)))
        return VehicleSnapshot(vehicle, ids)

    def list(self):
        return [self.get(identifier) for identifier in self.session.scalars(select(VehicleModel.vehicle_id).order_by(VehicleModel.vehicle_id))]

    def save(self, vehicle, accepted_connector_ids):
        if not accepted_connector_ids:
            raise InputError('Select at least one accepted connector.')
        saved = super().save(vehicle)
        self.session.execute(delete(VehicleAcceptsModel).where(VehicleAcceptsModel.vehicle_id == saved.vehicle_id))
        self.session.add_all([VehicleAcceptsModel(vehicle_id=saved.vehicle_id, connector_type_id=identifier)
                              for identifier in sorted(set(accepted_connector_ids))])
        self.session.flush()
        return self.get(saved.vehicle_id)


class StationRepository:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def get(self, identifier):
        item = self.session.get(StationModel, identifier)
        if item is None:
            return None
        ports = tuple(to_domain(Port, port) for port in self.session.scalars(select(PortModel).where(PortModel.station_id == identifier).order_by(PortModel.port_id)))
        periods = tuple(to_domain(OperatingPeriod, period) for period in self.session.scalars(select(OperatingPeriodModel).where(OperatingPeriodModel.station_id == identifier).order_by(OperatingPeriodModel.operating_period_id)))
        connector_ids = {port.connector_type_id for port in ports}
        connectors = tuple(to_domain(ConnectorType, model) for model in self.session.scalars(select(ConnectorTypeModel).where(ConnectorTypeModel.connector_type_id.in_(connector_ids)).order_by(ConnectorTypeModel.connector_type_id)))
        organization_ids = {item.owner_id, item.operator_id, item.network_id} - {None}
        organizations = tuple(to_domain(Organization, model) for model in self.session.scalars(select(OrganizationModel).where(OrganizationModel.organization_id.in_(organization_ids)).order_by(OrganizationModel.organization_id)))
        return StationSnapshot(to_domain(Station, item), ports, periods, connectors, organizations, station_metadata(self.settings, identifier))

    def list(self):
        return [self.get(identifier) for identifier in self.session.scalars(select(StationModel.station_id).order_by(StationModel.station_id))]


class CatalogRepository:
    def __init__(self, session):
        self.session = session

    def connectors(self):
        return [to_domain(ConnectorType, item) for item in self.session.scalars(select(ConnectorTypeModel).order_by(ConnectorTypeModel.connector_type_id))]

    def networks(self):
        return [to_domain(Organization, item) for item in self.session.scalars(select(OrganizationModel).join(NetworkModel).order_by(OrganizationModel.organization_id))]
