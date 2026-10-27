from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class NetworkModel(Base):
    __tablename__ = 'network'
    __table_args__ = ({'sqlite_with_rowid': False},)
    organization_id = mapped_column(Integer, ForeignKey('organization.organization_id', ondelete='CASCADE'), primary_key=True, autoincrement=False, nullable=False)
    payment_method = mapped_column(String(200), nullable=True)
