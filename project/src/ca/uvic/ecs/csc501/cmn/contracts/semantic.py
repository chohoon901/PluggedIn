"""Read models for the charging queries answered by the knowledge graph."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HighPowerPort:
    # 포트가 속한 충전소의 이름입니다. 원본에 없으면 None입니다.
    station_name: str | None
    # 출처에 기록된 DC 출력 상한입니다. 단위는 kW입니다.
    power_kw: Decimal
    # 이 포트에 달린 커넥터의 원문 이름입니다.
    connector_name: str
    # 출력값이 개별 포트 정격인지 운영사가 발표한 그룹 최대값인지 구분합니다.
    power_scope: str
    # 출력 근거의 웹 주소입니다. 그래프에 없으면 None입니다.
    source_url: str | None
    # 출력 근거를 확인한 날짜입니다. 그래프에 없으면 None입니다.
    checked_on: str | None


@dataclass(frozen=True, slots=True)
class SemanticVehicle:
    # 그래프에서 차량 한 대를 구별하는 리소스 주소입니다.
    iri: str
    # 차량의 모델 표시명입니다. 그래프에 없으면 None입니다.
    model: str | None


@dataclass(frozen=True, slots=True)
class AdapterCandidate:
    # 후보 포트가 속한 충전소의 이름입니다. 그래프에 없으면 None입니다.
    station_name: str | None
    # 방향이 일치하는 카탈로그 제품의 모델명입니다.
    adapter_model: str
    # 충전소 포트 쪽 커넥터 규격의 원문 이름입니다.
    port_connector: str
    # 차량 쪽 충전구 규격의 원문 이름입니다.
    vehicle_connector: str
    # 충전소 포트의 전류 유형입니다. 미확인이면 None입니다.
    port_current: str | None
    # 어댑터 카탈로그 자료의 웹 주소입니다. 그래프에 없으면 None입니다.
    source_url: str | None
    # 어댑터가 지원한다고 기록된 전류 유형입니다. 미확인이면 None입니다.
    adapter_current: str | None = None


class SemanticRepository(Protocol):
    def fast_chargers(self) -> list[HighPowerPort]: ...

    def vehicles(self) -> list[SemanticVehicle]: ...

    def adapter_candidates(self, vehicle_iri: str) -> list[AdapterCandidate]: ...
