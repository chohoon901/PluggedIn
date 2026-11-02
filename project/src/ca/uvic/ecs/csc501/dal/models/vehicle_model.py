from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class VehicleModel(Base):
    __tablename__ = 'vehicle'
    __table_args__ = (UniqueConstraint('vin', name='ak_vehicle_vin'), CheckConstraint('range_km > 0'), CheckConstraint('max_charge_kw > 0'),)
    vehicle_id = mapped_column(Integer, primary_key=True, nullable=False)
    vin = mapped_column(CHAR(17), nullable=False)
    licence_plate = mapped_column(String(15), nullable=True)
    make = mapped_column(String(50), nullable=True)
    model = mapped_column(String(50), nullable=True)
    vehicle_class = mapped_column('class', String(30), nullable=True)
    range_km = mapped_column(Integer, nullable=True)
    max_charge_kw = mapped_column(Numeric(6,1), nullable=True)
