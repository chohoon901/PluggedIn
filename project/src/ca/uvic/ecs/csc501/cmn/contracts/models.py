from dataclasses import dataclass
from ..vehicle import Vehicle
from ..station import Station
from ..port import Port
from ..operating_period import OperatingPeriod
from ..connector_type import ConnectorType
from ..organization import Organization


@dataclass(frozen=True)
class VehicleSnapshot:
    # DB에 등록된 차량 본체와 사양입니다. 운전자 소유 관계를 뜻하지 않습니다.
    vehicle: Vehicle
    # 이 차량이 직접 받는다고 등록한 커넥터 규격 번호들입니다.
    accepted_connector_ids: tuple[int, ...]

    def accepts(self, connector_id: int) -> bool:
        return connector_id in self.accepted_connector_ids


@dataclass(frozen=True)
class StationMetadata:
    # 시설 현지 시간을 구하는 IANA 시간대입니다. None이면 시간대를 모릅니다.
    timezone: str | None = None
    # 시간표 조사 범위입니다. COMPLETE일 때만 없는 요일을 휴무로 확정합니다.
    hours_completeness: str = 'UNKNOWN'
    # 포트 목록 조사 범위입니다. COMPLETE가 아니면 미확인 후보가 남습니다.
    ports_completeness: str = 'UNKNOWN'
    # 필수 부속 정보가 모두 조사되었는지 나타냅니다. INCOMPLETE는 불완전 시설입니다.
    aggregate_completeness: str = 'INCOMPLETE'
    # 운전자에게 보여 줄 자료의 출처 이름입니다.
    source_label: str = 'Unknown source'
    # 출처가 갱신된 시각입니다. None이면 갱신일을 모릅니다.
    source_updated_at: str | None = None
    # 외부 자료에 없어 DB 기본값만 적용된 미확인 필드 이름들입니다.
    unconfirmed_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class StationSnapshot:
    # 충전소의 주소·좌표·공통 이용 조건입니다.
    station: Station
    # 조사된 포트 항목들입니다. 빈 목록은 실제 포트가 없다는 확정이 아닙니다.
    ports: tuple[Port, ...]
    # 현지 요일별 개점 포함·폐점 제외 운영 구간들입니다.
    operating_periods: tuple[OperatingPeriod, ...]
    # 포트의 규격 번호를 해석하는 커넥터 사전입니다.
    connector_types: tuple[ConnectorType, ...]
    # 소유자·운영사·네트워크 이름을 표시하기 위한 기관 정보입니다.
    organizations: tuple[Organization, ...]
    # 원본 SQL에 없는 시간대·조사 완전성·출처 정보입니다.
    metadata: StationMetadata
