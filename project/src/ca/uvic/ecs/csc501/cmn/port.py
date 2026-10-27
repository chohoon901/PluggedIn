from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError
from decimal import Decimal


@dataclass(frozen=True)
class Port:
    # 충전소 안의 포트 또는 공급자가 묶어 기록한 포트 항목을 구별하는 번호입니다. 실시간 가용 포트 수가 아닙니다. 새로 등록해 번호를 받기 전에는 None입니다.
    port_id: int | None
    # 이 포트 항목이 설치된 충전소를 가리키는 번호입니다.
    station_id: int
    # 같은 충전소 안에서 이 포트 항목을 구별하는 양의 번호입니다. 다른 충전소에서는 같은 번호를 쓸 수 있습니다.
    number: int
    # 이 포트가 제공하는 커넥터 규격을 가리킵니다. 차량이 받는 규격과 비교합니다.
    connector_type_id: int
    # 이 포트 항목에 기록된 출력 상한입니다. 단위는 kW이며 실제 충전 속도는 차량·환경에 따라 달라집니다. None이면 등록되지 않은 선택 정보입니다.
    power_kw: Decimal | None = None
    # 포트가 공급하는 전기의 종류입니다. AC는 교류, DC는 직류이며 None이면 확인되지 않았습니다.
    current_type: str | None = None
    # 공급자가 이 항목에 묶어 기록한 개수입니다. 기본값은 1이며 물리 포트/커넥터 중 무엇을 세었는지는 별도 근거로 확인합니다.
    quantity: int = 1

    def __post_init__(self):
        validate_entity(self, {'current_type': 5}, ())
        if self.current_type not in (None, 'AC', 'DC'):
            raise InputError('The current type must be AC or DC.')
