from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError
from decimal import Decimal


@dataclass(frozen=True)
class ConnectorType:
    # 커넥터 규격 한 종류를 구별하는 번호입니다. 개별 충전기나 포트의 번호가 아닙니다. 새로 등록해 번호를 받기 전에는 None입니다.
    connector_type_id: int | None
    # 충전기 플러그·차량 충전구의 규격 이름입니다. 예: CCS1. 이름 별칭은 별도 검수합니다.
    name: str
    # 해당 규격에 대해 기록된 최대 출력 참고값입니다. 단위는 kW이며 모든 제품의 실제 속도를 보장하지 않습니다. None이면 등록되지 않은 선택 정보입니다.
    max_power_kw: Decimal | None = None

    def __post_init__(self):
        validate_entity(self, {'name': 100}, ('name',))
