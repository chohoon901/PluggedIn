from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class PortModel(Base):
    __tablename__ = 'port'
    __table_args__ = (UniqueConstraint('station_id', 'number', name='ak_port'), CheckConstraint('number > 0'), CheckConstraint('power_kw > 0'), CheckConstraint("current_type IN ('AC', 'DC')"), CheckConstraint('quantity > 0'), Index('ix_port_connector', 'connector_type_id'),)
    port_id = mapped_column(Integer, primary_key=True, nullable=False)
    station_id = mapped_column(Integer, ForeignKey('station.station_id', ondelete='CASCADE'), nullable=False)
    number = mapped_column(SmallInteger, nullable=False)
    connector_type_id = mapped_column(Integer, ForeignKey('connector_type.connector_type_id'), nullable=False)
    power_kw = mapped_column(Numeric(6,1), nullable=True)
    current_type = mapped_column(String(5), nullable=True)
    quantity = mapped_column(SmallInteger, nullable=False, server_default=text('1'))
