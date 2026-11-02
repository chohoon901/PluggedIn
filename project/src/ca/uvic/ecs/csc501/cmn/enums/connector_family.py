"""Source-name equivalence, independent of storage IDs and HTTP frameworks."""
from enum import StrEnum


class ConnectorFamily(StrEnum):
    # 같은 물리 규격의 출처별 이름을 비교하기 위한 분류입니다. DB 원문을 바꾸지 않습니다.
    J1772 = 'J1772'
    CCS1 = 'CCS1'
    CCS2 = 'CCS2'
    CHADEMO = 'CHADEMO'
    NACS = 'NACS'
    TYPE2 = 'TYPE2'
    NEMA515 = 'NEMA515'
    NEMA520 = 'NEMA520'
    NEMA1450 = 'NEMA1450'
    NEMA615 = 'NEMA615'
    NEMA620 = 'NEMA620'
    MCS = 'MCS'
    UNKNOWN = 'UNKNOWN'

    @classmethod
    def from_name(cls, name: str | None) -> 'ConnectorFamily':
        return _ALIASES.get(' '.join((name or '').upper().split()), cls.UNKNOWN)

    @property
    def verified_current(self) -> str | None:
        return {self.J1772: 'AC', self.CCS1: 'DC', self.CHADEMO: 'DC'}.get(self)


_ALIASES = {}
for _family, _names in {
    ConnectorFamily.J1772: ('J1772', 'Type 1 (J1772)', 'SAE J1772', 'SAE J1772-2009'),
    ConnectorFamily.CCS1: ('CCS1', 'CCS (Type 1)', 'J1772COMBO', 'CCS Type 1', 'CCS Combo 1'),
    ConnectorFamily.CCS2: ('CCS2', 'CCS (Type 2)', 'CCS Type 2', 'CCS Combo 2'),
    ConnectorFamily.CHADEMO: ('CHAdeMO',),
    ConnectorFamily.NACS: ('TESLA', 'NACS', 'NACS / Tesla Supercharger', 'Tesla (Model S/X)', 'J3400'),
    ConnectorFamily.TYPE2: ('Type 2', 'Type 2 (Socket Only)', 'Type 2 (Tethered Connector)'),
    ConnectorFamily.NEMA515: ('NEMA515', 'NEMA 5-15', 'NEMA 5-15R'),
    ConnectorFamily.NEMA520: ('NEMA520', 'NEMA 5-20', 'NEMA 5-20R'),
    ConnectorFamily.NEMA1450: ('NEMA1450', 'NEMA 14-50'),
    ConnectorFamily.NEMA615: ('NEMA615', 'NEMA 6-15'),
    ConnectorFamily.NEMA620: ('NEMA620', 'NEMA 6-20'),
    ConnectorFamily.MCS: ('J3271', 'MCS'),
}.items():
    for _name in _names:
        _ALIASES[' '.join(_name.upper().split())] = _family
