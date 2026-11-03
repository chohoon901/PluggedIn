"""NLR maximum_vehicle_class codes; interpretation never rewrites stored data."""
from enum import StrEnum


class VehicleClass(StrEnum):
    # NLR의 Class 1-2 승용·경량 차량 분류입니다.
    LD = 'LD'
    # NLR의 Class 3-6 중형 차량 분류입니다.
    MD = 'MD'
    # NLR의 Class 7-8 대형 차량 분류입니다.
    HD = 'HD'
    # 누락·미지원 값이나 차체 형태만으로 등급을 정할 수 없는 경우입니다.
    UNKNOWN = 'UNKNOWN'

    @classmethod
    def from_name(cls, name: str | None) -> 'VehicleClass':
        return _CODES.get(' '.join((name or '').upper().split()), cls.UNKNOWN)

    @classmethod
    def accepts_input(cls, name: str) -> bool:
        return cls.from_name(name) != cls.UNKNOWN

    @property
    def rank(self) -> int | None:
        return {self.LD: 0, self.MD: 1, self.HD: 2}.get(self)

    @property
    def label(self) -> str:
        return {self.LD: 'Light-duty / passenger vehicles (Class 1-2)',
                self.MD: 'Medium-duty vehicles (Class 3-6)',
                self.HD: 'Heavy-duty vehicles (Class 7-8)',
                self.UNKNOWN: 'Vehicle class unknown'}[self]


_CODES = {
    'LD': VehicleClass.LD, 'MD': VehicleClass.MD, 'HD': VehicleClass.HD,
}
