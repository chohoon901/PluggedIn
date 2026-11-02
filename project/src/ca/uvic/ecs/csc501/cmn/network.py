from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError


@dataclass(frozen=True)
class Network:
    # 멤버십·결제 서비스를 제공하는 충전 네트워크 기관의 번호입니다. network_id FK가 이 번호를 참조합니다.
    organization_id: int
    # 네트워크가 안내한 결제 방식 설명입니다. 이 문장만으로 게스트 결제 가능 여부를 확정하지 않습니다. None이면 등록되지 않은 선택 정보입니다.
    payment_method: str | None = None

    def __post_init__(self):
        validate_entity(self, {'payment_method': 200}, ())
