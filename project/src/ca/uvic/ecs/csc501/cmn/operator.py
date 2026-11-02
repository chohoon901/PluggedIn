from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError


@dataclass(frozen=True)
class Operator:
    # 충전 설비를 운영·관리하는 기관을 가리킵니다. 소유자 또는 네트워크와 다른 회사일 수 있습니다.
    organization_id: int
    # 충전 설비 이용 문제를 문의할 운영사의 전화번호입니다. 운전자의 전화번호가 아닙니다. None이면 등록되지 않은 선택 정보입니다.
    support_phone: str | None = None

    def __post_init__(self):
        validate_entity(self, {'support_phone': 30}, ())
