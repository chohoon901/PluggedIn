from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class SiteOwnerModel(Base):
    __tablename__ = 'site_owner'
    __table_args__ = ({'sqlite_with_rowid': False},)
    organization_id = mapped_column(Integer, ForeignKey('organization.organization_id', ondelete='CASCADE'), primary_key=True, autoincrement=False, nullable=False)
    business_type = mapped_column(String(100), nullable=True)
