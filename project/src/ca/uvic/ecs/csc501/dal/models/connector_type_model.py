from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class ConnectorTypeModel(Base):
    __tablename__ = 'connector_type'
    __table_args__ = (UniqueConstraint('name', name='ak_connector_type_name'), CheckConstraint('max_power_kw > 0'),)
    connector_type_id = mapped_column(Integer, primary_key=True, nullable=False)
    name = mapped_column(String(100), nullable=False)
    max_power_kw = mapped_column(Numeric(6,1), nullable=True)
