from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class AdapterModel(Base):
    __tablename__ = 'adapter'
    __table_args__ = (UniqueConstraint('model', name='ak_adapter_model'), CheckConstraint('max_power_kw > 0'), CheckConstraint('from_connector_type_id <> to_connector_type_id', name='ck_adapter_direction'), Index('ix_adapter_from', 'from_connector_type_id'), Index('ix_adapter_to', 'to_connector_type_id'),)
    adapter_id = mapped_column(Integer, primary_key=True, nullable=False)
    model = mapped_column(String(100), nullable=False)
    manufacturer = mapped_column(String(100), nullable=True)
    max_power_kw = mapped_column(Numeric(6,1), nullable=True)
    from_connector_type_id = mapped_column(Integer, ForeignKey('connector_type.connector_type_id'), nullable=False)
    to_connector_type_id = mapped_column(Integer, ForeignKey('connector_type.connector_type_id'), nullable=False)
