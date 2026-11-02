from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError


@dataclass(frozen=True)
class SiteOwner:
    # 충전소 부지나 시설을 소유한 기관을 가리키는 번호입니다. organization의 같은 번호를 사용합니다.
    organization_id: int
    # 부지 소유자의 업종이나 시설 종류입니다. 예: 쇼핑센터·숙박시설. 충전 커넥터 종류가 아닙니다. None이면 등록되지 않은 선택 정보입니다.
    business_type: str | None = None

    def __post_init__(self):
        validate_entity(self, {'business_type': 100}, ())
