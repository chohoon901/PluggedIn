from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError


@dataclass(frozen=True)
class VehicleAccepts:
    # 차량과 수용 가능한 커넥터 규격의 연결 기록 하나를 구별하는 번호입니다. 새로 등록해 번호를 받기 전에는 None입니다.
    vehicle_accepts_id: int | None
    # 해당 커넥터를 받아들일 수 있다고 기록한 차량의 내부 번호입니다.
    vehicle_id: int
    # 이 차량이 수용한다고 기록된 커넥터 규격 번호입니다. 원본 테이블에는 차량별 AC/DC 추가 정보가 없으므로 규격만으로 확정할 수 없는 연결은 확인 필요로 처리합니다.
    connector_type_id: int

    def __post_init__(self):
        validate_entity(self, {}, ())
