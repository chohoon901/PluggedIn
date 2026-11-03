"""Schema-preserving adapter reference; not used in connection evaluation."""
from dataclasses import dataclass
from decimal import Decimal

from .validation import validate_entity
from ..contracts.errors import InputError


@dataclass(frozen=True)
class Adapter:
    # 어댑터 모델 하나를 구별하는 번호입니다. 운전자가 소유한 실물의 일련번호가 아닙니다.
    adapter_id: int | None
    # 어댑터 제품 모델명입니다. 원본 스키마에서 같은 모델명을 중복 저장하지 않습니다.
    model: str
    # 제조사 이름입니다. None이면 제조사가 등록되지 않았습니다.
    manufacturer: str | None
    # 기록된 출력 상한(kW)입니다. None이면 허용 출력을 확인할 수 없습니다.
    max_power_kw: Decimal | None
    # 충전기 쪽 플러그 규격입니다. 방향만 맞아도 호환이 검증된 것은 아닙니다.
    from_connector_type_id: int
    # 차량 쪽 충전구 규격입니다. 반대 방향 사용 가능성을 뜻하지 않습니다.
    to_connector_type_id: int

    def __post_init__(self):
        validate_entity(self, {'model': 100, 'manufacturer': 100}, ('model',))
        if self.from_connector_type_id == self.to_connector_type_id:
            raise InputError('The connector types on each end of the adapter must differ.')
