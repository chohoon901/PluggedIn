from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class CheckStatus(str, Enum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    UNKNOWN = 'UNKNOWN'


class OverallStatus(str, Enum):
    AVAILABLE = 'AVAILABLE'
    UNAVAILABLE = 'UNAVAILABLE'
    NEEDS_REVIEW = 'NEEDS_REVIEW'


class ReasonCode(str, Enum):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    HOURS_UNKNOWN = 'HOURS_UNKNOWN'
    TIMEZONE_UNKNOWN = 'TIMEZONE_UNKNOWN'
    FACILITY_STATUS_UNKNOWN = 'FACILITY_STATUS_UNKNOWN'
    ACCESS_PUBLIC = 'ACCESS_PUBLIC'
    ACCESS_DENIED = 'ACCESS_DENIED'
    ACCESS_RESTRICTED_UNKNOWN = 'ACCESS_RESTRICTED_UNKNOWN'
    VEHICLE_TOO_LARGE = 'VEHICLE_TOO_LARGE'
    VEHICLE_CLASS_UNKNOWN = 'VEHICLE_CLASS_UNKNOWN'
    TRUCK_CLEARANCE_UNKNOWN = 'TRUCK_CLEARANCE_UNKNOWN'
    DIRECT_COMPATIBLE = 'DIRECT_COMPATIBLE'
    DIRECT_INCOMPATIBLE = 'DIRECT_INCOMPATIBLE'
    CONNECTOR_UNKNOWN = 'CONNECTOR_UNKNOWN'
    PORTS_UNKNOWN = 'PORTS_UNKNOWN'
    MEMBERSHIP_ACCEPTED = 'MEMBERSHIP_ACCEPTED'
    GUEST_PAYMENT_ACCEPTED = 'GUEST_PAYMENT_ACCEPTED'
    NO_PAYMENT_OPTION = 'NO_PAYMENT_OPTION'
    PAYMENT_UNKNOWN = 'PAYMENT_UNKNOWN'
    POWER_UNKNOWN = 'POWER_UNKNOWN'


@dataclass(frozen=True)
class Reason:
    # 화면·API가 공유하는 판정 이유 코드입니다.
    code: ReasonCode
    # 비전공자가 판정 근거를 이해하도록 설명한 문장입니다.
    message: str


@dataclass(frozen=True)
class CheckResult:
    # 이 항목의 충족·불충족·미확인 상태입니다.
    status: CheckStatus
    # 이 항목의 상태를 설명하는 이유들입니다.
    reasons: tuple[Reason, ...]
    # 계산에 실제 사용한 DB 값과 현지 시각 등 근거입니다.
    evidence: dict


@dataclass(frozen=True)
class EvaluationResult:
    # 평가한 충전소 내부 번호입니다.
    station_id: int
    # 멤버십을 조회한 운전자의 내부 번호입니다.
    driver_id: int
    # 직접 연결과 크기를 비교한 차량 내부 번호입니다.
    vehicle_id: int
    # 호출자가 한 번 확정해 전달한 시간대 포함 도착 시각입니다.
    arrival_at: datetime
    # 선택 포트 후보의 opening/access/connector/payment 네 항목입니다.
    checks: dict[str, CheckResult]
    # 포트별 네 항목을 AND하고 후보들을 OR한 종합 상태입니다.
    overall_status: OverallStatus
    # 직접 규격과 전류가 검증된 포트 번호들을 후보 우선순위로 정렬한 값입니다.
    compatible_port_ids: tuple[int, ...]
    # 결과를 설명하는 대표 포트 번호입니다. 미확인 후보이면 None입니다.
    selected_port_id: int | None
    # 포트와 차량 출력의 작은 상한(kW)입니다. 하나라도 미상이면 None입니다.
    power_limit_kw: Decimal | None
    # 출력 미상처럼 호환 결과와 구별해 안내할 사항입니다.
    warnings: tuple[Reason, ...]


@dataclass(frozen=True)
class EvaluationPolicy:
    """The approved conservative MVP policy; no clock or storage dependencies."""
