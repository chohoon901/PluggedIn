from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError


@dataclass(frozen=True)
class Organization:
    # 이 기관이나 회사 하나를 서비스 안에서 구별하는 번호입니다. 사업자등록번호가 아닙니다. 새로 등록해 번호를 받기 전에는 None입니다.
    organization_id: int | None
    # 기관이나 회사의 이름입니다. 예: 충전 네트워크 회사명. 서로 다른 조직을 이름만으로 자동 합치지 않습니다.
    name: str
    # 이 기관이 안내하는 웹사이트 주소입니다. None이면 등록된 주소가 없습니다.
    website: str | None = None

    def __post_init__(self):
        validate_entity(self, {'name': 200, 'website': 300}, ('name',))
