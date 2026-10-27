from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from ..contracts.errors import InputError


def decimal_value(value, field: str, *, low=None, high=None, positive=False, places='0.1'):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or (low is not None and number < low) or (high is not None and number > high) or (positive and number <= 0):
            raise ValueError
        normalized = number.quantize(Decimal(places))
        if positive and normalized <= 0:
            raise ValueError
        return normalized
    except (InvalidOperation, ValueError, TypeError):
        raise InputError(f'{field}: enter a number within the allowed range.', {field: 'Enter a number within the allowed range.'}) from None


@dataclass(frozen=True)
class Location:
    # 위도입니다. 도 단위이며 북위는 양수이고 -90에서 90까지 허용합니다.
    latitude: Decimal
    # 경도입니다. 도 단위이며 서경은 음수이고 -180에서 180까지 허용합니다.
    longitude: Decimal

    def __post_init__(self):
        object.__setattr__(self, 'latitude', decimal_value(self.latitude, 'latitude', low=-90, high=90, places='0.000001'))
        object.__setattr__(self, 'longitude', decimal_value(self.longitude, 'longitude', low=-180, high=180, places='0.000001'))
