from sqlalchemy import Integer, SmallInteger, String, CHAR, Numeric, Boolean, Date, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import mapped_column
from .base import Base


class OperatingPeriodModel(Base):
    __tablename__ = 'operating_period'
    __table_args__ = (
        UniqueConstraint('station_id', 'day', 'open_time', name='ak_operating_period'),
        CheckConstraint("day IN ('Mon','Tue','Wed','Thu','Fri','Sat','Sun')"),
        CheckConstraint('close_time > open_time', name='ck_operating_period_order'),
        CheckConstraint("length(open_time)=8 AND open_time GLOB '[0-2][0-9]:[0-5][0-9]:[0-5][0-9]' AND open_time<'24:00:00'", name='ck_open_clock'),
        CheckConstraint("close_time='24:00:00' OR (length(close_time)=8 AND close_time GLOB '[0-2][0-9]:[0-5][0-9]:[0-5][0-9]' AND close_time<'24:00:00')", name='ck_close_clock'),
    )
    operating_period_id = mapped_column(Integer, primary_key=True, nullable=False)
    station_id = mapped_column(Integer, ForeignKey('station.station_id', ondelete='CASCADE'), nullable=False)
    day = mapped_column(String(3), nullable=False)
    open_time = mapped_column(Text, nullable=False)
    close_time = mapped_column(Text, nullable=False)
