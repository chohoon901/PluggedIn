from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError


@dataclass(frozen=True)
class Driver:
    # DB의 운전자 한 명을 구별하는 내부 번호입니다. 로그인 계정이나 브라우저 추적 ID가 아닙니다. 새로 등록해 번호를 받기 전에는 None입니다.
    driver_id: int | None
    # 실제 세계의 운전면허번호에 대응하는 필드입니다. 운전자 등록·수정 폼에서 입력받아 driver 테이블에 저장합니다.
    licence_number: str
    # 운전자의 이름에 대응하는 필드입니다. 운전자 등록·수정 폼에서 입력받아 저장합니다. None이면 등록되지 않은 선택 정보입니다.
    name: str | None = None
    # 운전자가 속한 운송사 이름입니다. 충전 네트워크 이름과 다르며 운전자 등록·수정 폼에서 입력받아 저장합니다. None이면 등록되지 않은 선택 정보입니다.
    carrier_name: str | None = None

    def __post_init__(self):
        validate_entity(self, {'licence_number': 30, 'name': 100, 'carrier_name': 200}, ('licence_number',))
