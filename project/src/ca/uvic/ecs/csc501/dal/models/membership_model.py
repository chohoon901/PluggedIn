from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class MembershipModel(Base):
    __tablename__ = 'membership'
    __table_args__ = (UniqueConstraint('driver_id', 'network_id', 'start_date', name='ak_membership'), CheckConstraint('end_date IS NULL OR end_date >= start_date', name='ck_membership_dates'), Index('ix_membership_network', 'network_id'),)
    membership_id = mapped_column(Integer, primary_key=True, nullable=False)
    driver_id = mapped_column(Integer, ForeignKey('driver.driver_id', ondelete='CASCADE'), nullable=False)
    network_id = mapped_column(Integer, ForeignKey('network.organization_id', ondelete='CASCADE'), nullable=False)
    start_date = mapped_column(Date, nullable=False)
    end_date = mapped_column(Date, nullable=True)
