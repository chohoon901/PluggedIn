"""HTTP inputs; application services independently enforce domain rules."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    @field_validator('*', mode='before')
    @classmethod
    def empty_optional(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class DriverInput(InputModel):
    # 실제 운전면허번호입니다. 공백만 입력할 수 없으며 최대 30자입니다.
    licence_number: str = Field(min_length=1, max_length=30)
    # 운전자 이름이며 비어 있으면 등록하지 않습니다.
    name: str | None = Field(default=None, max_length=100)
    # 운전자가 속한 운송사 이름이며 미입력은 None입니다.
    carrier_name: str | None = Field(default=None, max_length=200)

    @field_validator('licence_number', mode='before')
    @classmethod
    def licence_without_spaces(cls, value):
        return ''.join(value.split()) if isinstance(value, str) else value


class VehicleInput(InputModel):
    # 차량의 17자리 차대번호이며 등록에 반드시 필요합니다.
    vin: str = Field(min_length=17, max_length=17)
    # 번호판 표시이며 없으면 None입니다.
    licence_plate: str | None = Field(default=None, max_length=15)
    # 차량 제조사 이름이며 없으면 None입니다.
    make: str | None = Field(default=None, max_length=50)
    # 차량 모델 이름이며 없으면 None입니다.
    model: str | None = Field(default=None, max_length=50)
    # 차량 등급 문자열입니다. 법정 중량 분류를 대신하지 않습니다.
    vehicle_class: str | None = Field(default=None, max_length=30)
    # 참고 주행 거리(km)이며 현재 배터리 잔량에 따른 거리가 아닙니다.
    range_km: int | None = Field(default=None, gt=0)
    # 차량 충전 출력 상한(kW)이며 미입력은 출력 미상입니다.
    max_charge_kw: Decimal | None = Field(default=None, gt=0, le=99999.9)
    # 직접 연결을 수용하는 커넥터 규격 번호들로 최소 하나 필요합니다.
    accepted_connector_ids: list[int] = Field(min_length=1)

    @field_validator('accepted_connector_ids')
    @classmethod
    def connectors(cls, value):
        if any(item <= 0 for item in value):
            raise ValueError('Connector IDs must be positive integers.')
        return sorted(set(value))


class MembershipInput(InputModel):
    # 가입 기록을 연결할 운전자의 내부 번호입니다.
    driver_id: int = Field(gt=0)
    # 가입 네트워크 조직의 내부 번호입니다.
    network_id: int = Field(gt=0)
    # 현지 날짜 기준 첫 유효일이며 이 날짜를 포함합니다.
    start_date: date
    # 마지막 유효일이며 없으면 종료일 미지정입니다.
    end_date: date | None = None

    @model_validator(mode='after')
    def dates_in_order(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError('The end date cannot be before the start date.')
        return self


class BoundingBox(InputModel):
    # 검색 영역 서쪽 경계의 경도(도)입니다.
    west: float = Field(ge=-180, le=180)
    # 검색 영역 남쪽 경계의 위도(도)입니다.
    south: float = Field(ge=-90, le=90)
    # 검색 영역 동쪽 경계의 경도(도)입니다.
    east: float = Field(ge=-180, le=180)
    # 검색 영역 북쪽 경계의 위도(도)입니다.
    north: float = Field(ge=-90, le=90)

    @model_validator(mode='after')
    def ordered(self):
        if self.west >= self.east or self.south >= self.north:
            raise ValueError('The west bound must be less than east, and south less than north.')
        return self


class EvaluationInput(InputModel):
    # 평가에 사용할 DB 운전자 번호입니다.
    driver_id: int = Field(gt=0)
    # 운전자와 독립적으로 선택한 DB 차량 번호입니다.
    vehicle_id: int = Field(gt=0)
    # Z 또는 UTC offset이 있는 도착 시각이며 None이면 요청 시 현재입니다.
    arrival_at: datetime | None = None

    @field_validator('arrival_at')
    @classmethod
    def aware(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError('Include Z or a UTC offset such as +00:00 in the arrival time.')
        return value


class SearchInput(EvaluationInput):
    # 선택한 지도 검색 영역입니다.
    bbox: BoundingBox
    # 화면에 표시할 종합 판정 상태이며 ALL은 전체입니다.
    status: Literal['ALL', 'AVAILABLE', 'NEEDS_REVIEW', 'UNAVAILABLE'] = 'ALL'
