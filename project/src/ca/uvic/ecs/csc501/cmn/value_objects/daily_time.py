"""A local clock value, including the exclusive end-of-day boundary."""
from dataclasses import dataclass
import re
from ..contracts.errors import InputError


@dataclass(frozen=True, order=True)
class DailyTime:
    # 자정부터 지난 초입니다. 86400은 폐점 시각에만 사용하는 그날 끝의 자정입니다.
    seconds: int

    def __post_init__(self):
        if type(self.seconds) is not int or not 0 <= self.seconds <= 86400:
            raise InputError('The time must be between 0 and 86400 seconds after midnight.')

    @classmethod
    def parse(cls, value: str) -> 'DailyTime':
        if not isinstance(value, str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]|24:00:00', value):
            raise InputError('The time must use the HH:MM:SS format.')
        hours, minutes, seconds = map(int, value.split(':'))
        return cls(hours * 3600 + minutes * 60 + seconds)

    def __str__(self):
        hours, remainder = divmod(self.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f'{hours:02}:{minutes:02}:{seconds:02}'
