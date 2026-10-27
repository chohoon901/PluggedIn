from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError
from datetime import date


@dataclass(frozen=True)
class Membership:
    # 운전자의 네트워크 가입 기록 한 개를 구별하는 번호입니다. 카드 번호나 결제 인증 정보가 아닙니다. 새로 등록해 번호를 받기 전에는 None입니다.
    membership_id: int | None
    # 이 가입 기록의 운전자를 가리킵니다. 면허번호 자체를 저장하는 필드가 아닙니다.
    driver_id: int
    # 가입한 충전 네트워크의 조직 번호입니다. 충전소의 network_id와 비교합니다.
    network_id: int
    # 멤버십이 시작되는 현지 날짜입니다. 이 날짜를 포함합니다.
    start_date: date
    # 마지막 유효 날짜입니다. 이 날짜를 포함하고 None이면 종료일이 따로 기록되지 않은 상태입니다.
    end_date: date | None = None

    def __post_init__(self):
        validate_entity(self, {}, ())
        if type(self.start_date) is not date or (self.end_date is not None and type(self.end_date) is not date):
            raise InputError('Enter the membership dates.')
        if self.end_date is not None and self.end_date < self.start_date:
            raise InputError('The end date cannot be before the start date.', {'end_date': 'Enter a date on or after the start date.'})

    def is_active_on(self, local_date: date) -> bool:
        return self.start_date <= local_date and (self.end_date is None or local_date <= self.end_date)
