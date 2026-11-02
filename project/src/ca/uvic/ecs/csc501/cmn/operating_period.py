from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError
from datetime import datetime
from .value_objects.daily_time import DailyTime


@dataclass(frozen=True)
class OperatingPeriod:
    # 요일별 운영 구간 한 개를 구별하는 번호입니다. 충전 예약 번호가 아닙니다. 새로 등록해 번호를 받기 전에는 None입니다.
    operating_period_id: int | None
    # 이 운영시간이 적용되는 충전소 번호입니다.
    station_id: int
    # 충전소 현지 기준 요일입니다. Mon에서 Sun까지의 영문 세 글자를 사용합니다.
    day: str
    # 그 요일에 이용을 시작할 수 있는 현지 시각입니다. 이 시각을 포함하며 24:00은 시작값으로 쓰지 않습니다.
    open_time: DailyTime
    # 그 요일에 이용이 끝나는 현지 시각입니다. 이 시각은 포함하지 않으며 24:00은 그날 끝의 자정입니다. 야간은 날짜별 두 행으로 나눕니다.
    close_time: DailyTime

    def __post_init__(self):
        validate_entity(self, {'day': 3}, ('day',))
        if self.day not in ('Mon','Tue','Wed','Thu','Fri','Sat','Sun'):
            raise InputError('The day must be one of Mon through Sun.')
        if not isinstance(self.open_time, DailyTime) or not isinstance(self.close_time, DailyTime) or self.open_time.seconds >= 86400 or self.close_time <= self.open_time:
            raise InputError('Enter a closing time after the opening time. The opening time cannot be 24:00.')

    def contains(self, local_datetime: datetime) -> bool:
        weekday = ('Mon','Tue','Wed','Thu','Fri','Sat','Sun')[local_datetime.weekday()]
        seconds = local_datetime.hour * 3600 + local_datetime.minute * 60 + local_datetime.second + local_datetime.microsecond / 1000000
        return weekday == self.day and self.open_time.seconds <= seconds < self.close_time.seconds
