from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError
from decimal import Decimal


@dataclass(frozen=True)
class Vehicle:
    # DB의 차량 한 대를 구별하는 내부 번호입니다. 검색 시 선택한 차량을 가리키는 ID로 사용합니다. 새로 등록해 번호를 받기 전에는 None입니다.
    vehicle_id: int | None
    # 제조사가 차량 한 대에 부여한 17자리 차대번호입니다. 차량 등록 폼에서 입력받아 vehicle 테이블에 저장합니다.
    vin: str
    # 차량 번호판에 적힌 번호입니다. 차량 등록·수정 폼에서 입력받아 DB에 저장합니다. None이면 등록되지 않은 선택 정보입니다.
    licence_plate: str | None = None
    # 차량을 만든 회사나 브랜드 이름입니다. None이면 등록되지 않은 선택 정보입니다.
    make: str | None = None
    # 차량 모델 이름입니다. 같은 이름이어도 연식·사양에 따라 충전 조건이 다를 수 있습니다. None이면 등록되지 않은 선택 정보입니다.
    model: str | None = None
    # 차량 크기·종류의 등급입니다. Python 필드는 vehicle_class이며 원본 DB 컬럼 class에 매핑합니다. None이면 등록되지 않은 선택 정보입니다.
    vehicle_class: str | None = None
    # 기록된 주행 가능 거리의 참고값입니다. 단위는 km이며 현재 배터리로 갈 수 있는 거리가 아닙니다. None이면 등록되지 않은 선택 정보입니다.
    range_km: int | None = None
    # 차량에 기록된 최대 충전 출력입니다. 단위는 kW이며 모든 충전 상황에서 이 속도가 나오는 것은 아닙니다. None이면 등록되지 않은 선택 정보입니다.
    max_charge_kw: Decimal | None = None

    def __post_init__(self):
        validate_entity(self, {'vin': 17, 'licence_plate': 15, 'make': 50, 'model': 50, 'vehicle_class': 30}, ('vin',))
        if len(self.vin) != 17:
            raise InputError('The VIN must be exactly 17 characters.', {'vin': 'Enter exactly 17 characters.'})
