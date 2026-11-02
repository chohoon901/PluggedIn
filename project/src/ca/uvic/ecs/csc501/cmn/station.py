from dataclasses import dataclass
from .validation import validate_entity
from .contracts.errors import InputError
from decimal import Decimal
from .value_objects.location import Location


@dataclass(frozen=True)
class Station:
    # 충전소 한 곳을 프로그램 안에서 구별하는 번호입니다. 외부 제공자의 충전소 번호와 구분합니다. 새로 등록해 번호를 받기 전에는 None입니다.
    station_id: int | None
    # 충전소 위치의 위도입니다. 도 단위이며 북위는 양수, 허용 범위는 -90에서 90입니다.
    latitude: Decimal
    # 충전소 위치의 경도입니다. 도 단위이며 서경은 음수, 허용 범위는 -180에서 180입니다.
    longitude: Decimal
    # 운전자에게 보여 줄 충전소 이름입니다. 이름이 없을 수도 있습니다. None이면 등록되지 않은 선택 정보입니다.
    name: str | None
    # 충전소가 있는 도로명·번지 등 거리 주소입니다. 경도·위도와는 별개입니다. None이면 등록되지 않은 선택 정보입니다.
    street: str | None
    # 충전소가 속한 도시 이름입니다. 운전자의 거주 도시가 아닙니다. None이면 등록되지 않은 선택 정보입니다.
    city: str | None
    # 충전소가 속한 주 이름 또는 코드입니다. MVP는 BC 데이터를 대상으로 합니다. None이면 등록되지 않은 선택 정보입니다.
    province: str | None
    # 공개 데이터에 기록된 시설 상태입니다. 현재 포트의 고장·점유·대기 줄을 뜻하지 않습니다. None이면 등록되지 않은 선택 정보입니다.
    status: str | None
    # 누가 이곳을 이용할 수 있는지 설명한 제한입니다. 예: 고객 전용·플릿 전용. 도로 통행 허가를 대신하지 않습니다. None이면 등록되지 않은 선택 정보입니다.
    access_restriction: str | None
    # 멤버십 없이 결제를 받는지에 관한 DB 값입니다. 직접 입력·검수한 값은 그대로 사용하고 외부 수집 기본값인 경우 메타데이터에서 미확인으로 표시합니다.
    accepts_guest_payment: bool
    # 시설이 받을 수 있다고 안내한 차량 등급 제한입니다. 미기재를 모든 차량 허용으로 해석하지 않습니다. None이면 등록되지 않은 선택 정보입니다.
    max_vehicle_class: str | None
    # 트럭 주차 공간이 있다고 기록했는지 나타내는 DB 값입니다. 기본 false와 미확인은 다르며 충전 베이 진입을 보장하지 않습니다.
    has_truck_parking: bool
    # 이 충전소 부지·시설의 소유자 역할을 가리킵니다. site_owner의 조직 번호입니다.
    owner_id: int
    # 충전 설비를 실제 운영·관리하는 역할을 가리킵니다. operator의 조직 번호입니다.
    operator_id: int
    # 이 충전소에서 사용하는 충전 네트워크의 조직 번호입니다. None이면 연결된 네트워크가 기록되지 않았습니다.
    network_id: int | None

    def __post_init__(self):
        validate_entity(self, {'name': 200, 'street': 200, 'city': 100, 'province': 50, 'status': 50, 'access_restriction': 100, 'max_vehicle_class': 30}, ())
        location = Location(self.latitude, self.longitude)
        object.__setattr__(self, 'latitude', location.latitude)
        object.__setattr__(self, 'longitude', location.longitude)
        if type(self.accepts_guest_payment) is not bool or type(self.has_truck_parking) is not bool:
            raise InputError('Enter confirmed true or false values for the facility.')
