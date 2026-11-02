from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class OperatorModel(Base):
    __tablename__ = 'operator'
    __table_args__ = ({'sqlite_with_rowid': False},)
    organization_id = mapped_column(Integer, ForeignKey('organization.organization_id', ondelete='CASCADE'), primary_key=True, autoincrement=False, nullable=False)
    support_phone = mapped_column(String(30), nullable=True)
