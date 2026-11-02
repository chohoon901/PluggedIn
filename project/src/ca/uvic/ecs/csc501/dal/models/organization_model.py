from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class OrganizationModel(Base):
    __tablename__ = 'organization'
    __table_args__ = (UniqueConstraint('name', name='ak_organization_name'),)
    organization_id = mapped_column(Integer, primary_key=True, nullable=False)
    name = mapped_column(String(200), nullable=False)
    website = mapped_column(String(300), nullable=True)
