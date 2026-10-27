from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class VehicleAcceptsModel(Base):
    __tablename__ = 'vehicle_accepts'
    __table_args__ = (UniqueConstraint('vehicle_id', 'connector_type_id', name='ak_vehicle_accepts'), Index('ix_accepts_connector', 'connector_type_id'),)
    vehicle_accepts_id = mapped_column(Integer, primary_key=True, nullable=False)
    vehicle_id = mapped_column(Integer, ForeignKey('vehicle.vehicle_id', ondelete='CASCADE'), nullable=False)
    connector_type_id = mapped_column(Integer, ForeignKey('connector_type.connector_type_id'), nullable=False)
