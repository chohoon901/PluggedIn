from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class StationModel(Base):
    __tablename__ = 'station'
    __table_args__ = (UniqueConstraint('latitude', 'longitude', name='ak_station_location'), CheckConstraint('latitude BETWEEN -90 AND 90'), CheckConstraint('longitude BETWEEN -180 AND 180'), CheckConstraint('accepts_guest_payment IN (0,1)'), CheckConstraint('has_truck_parking IN (0,1)'), Index('ix_station_owner', 'owner_id'), Index('ix_station_operator', 'operator_id'), Index('ix_station_network', 'network_id'),)
    station_id = mapped_column(Integer, primary_key=True, nullable=False)
    latitude = mapped_column(Numeric(9,6), nullable=False)
    longitude = mapped_column(Numeric(9,6), nullable=False)
    name = mapped_column(String(200), nullable=True)
    street = mapped_column(String(200), nullable=True)
    city = mapped_column(String(100), nullable=True)
    province = mapped_column(String(50), nullable=True)
    status = mapped_column(String(50), nullable=True)
    access_restriction = mapped_column(String(100), nullable=True)
    accepts_guest_payment = mapped_column(Boolean, nullable=False, server_default=text('0'))
    max_vehicle_class = mapped_column(String(30), nullable=True)
    has_truck_parking = mapped_column(Boolean, nullable=False, server_default=text('0'))
    owner_id = mapped_column(Integer, ForeignKey('site_owner.organization_id'), nullable=False)
    operator_id = mapped_column(Integer, ForeignKey('operator.organization_id'), nullable=False)
    network_id = mapped_column(Integer, ForeignKey('network.organization_id'), nullable=True)
