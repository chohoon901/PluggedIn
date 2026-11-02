from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError
from decimal import Decimal


@dataclass(frozen=True)
class Adapter:
    # 어댑터 모델 하나를 구별하는 번호입니다. 특정 운전자가 소유한 실물 제품의 일련번호가 아닙니다. 새로 등록해 번호를 받기 전에는 None입니다.
    adapter_id: int | None
    # 어댑터 제품의 모델명입니다. 제공 DDL에서 같은 모델명을 중복 저장하지 않습니다.
    model: str
    # 어댑터를 만든 제조사 이름입니다. 차량 제조사와 항상 같지는 않습니다. None이면 등록되지 않은 선택 정보입니다.
    manufacturer: str | None
    # 어댑터가 허용한다고 기록된 출력 상한입니다. 단위는 kW이며 미기재면 최대 출력을 확정할 수 없습니다. None이면 등록되지 않은 선택 정보입니다.
    max_power_kw: Decimal | None
    # 어댑터의 충전기 쪽이 받아들이는 플러그 규격입니다. 반대 방향 사용 가능성을 뜻하지 않습니다.
    from_connector_type_id: int
    # 어댑터의 차량 쪽이 연결되는 충전구 규격입니다. 방향만 맞아도 실제 호환이 검증된 것은 아닙니다.
    to_connector_type_id: int

    def __post_init__(self):
        validate_entity(self, {'model': 100, 'manufacturer': 100}, ('model',))
        if self.from_connector_type_id == self.to_connector_type_id:
            raise InputError('The connector types on each end of the adapter must differ.')
