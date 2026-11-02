from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class DriverModel(Base):
    __tablename__ = 'driver'
    __table_args__ = (UniqueConstraint('licence_number', name='ak_driver_licence'),)
    driver_id = mapped_column(Integer, primary_key=True, nullable=False)
    licence_number = mapped_column(String(30), nullable=False)
    name = mapped_column(String(100), nullable=True)
    carrier_name = mapped_column(String(200), nullable=True)
