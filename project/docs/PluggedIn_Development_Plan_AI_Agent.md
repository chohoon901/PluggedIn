---
document_id: PLUGGEDIN-DEV-001
version: 3.0.0
date: 2026-10-26
language: ko
status: implementation-specification
delivery: self-contained-new-project-instructions
---

# PluggedIn — 새 프로젝트 구현용 개발 기획서

> **Agent에게:** 이 문서 하나를 입력으로 받아 새 Python 프로젝트와 실제 동작하는 학교 프로젝트 MVP를 구현한다. 별도 PDF·ERD·SQL·이전 기획서가 없어도 된다. §13의 SQLite DDL과 §14의 전체 필드 사전이 구현 기준이다. 계획만 다시 작성하거나 정적 목업·빈 함수로 끝내지 않는다. 이번 문서의 개정 작업 자체는 MVP 코드 작성과 구별한다.

## 1. 확정 요구사항과 우선순위

### 1.1 제품 목표

BC 전기차 운전자가 **DB에 등록한 운전자와 차량을 선택**하고 도착 시각을 지정하면, 충전소의 운영시간·이용/차량 제한·직접 커넥터 호환·결제 조건을 비교한다. 결과와 근거를 서버에서 계산하고 HTML로 렌더링한다. 충전소 위치만 보는 데서 끝나지 않고 이용이 어려운 이유를 확인할 수 있어야 한다.

대표 흐름은 운전자 등록 → 차량 및 수용 커넥터 등록 → 멤버십 등록 → 운전자/차량/도착 시각 선택 → 지도·목록 → 충전소 상세 → 외부 길찾기다.

### 1.2 전역 제약 — 사용자 최종 결정

1. Python venv, FastAPI, SQLAlchemy ORM, 로컬 SQLite를 사용한다.
2. **HTML/CSS/JS는 pl에 두며 FastAPI + Jinja2로 서버 사이드 렌더링(SSR)을 구현한다.** HTML 파일만 서버에서 보내고 본문을 JS의 API 호출로 채우는 방식은 요구를 충족하지 않는다.
3. **운전자·차량·멤버십 정보를 전부 DB에 저장한다.** 면허번호, 운전자 이름, 운송사 이름, VIN, 차량번호, 제조사·모델·등급·거리·출력, 수용 커넥터, 가입 네트워크·시작/종료일을 입력·저장·조회·수정·삭제한다.
4. 필수/선택은 §13 DDL의 NOT NULL에 따른다. “전부 저장”은 모든 필드를 지원한다는 뜻이며 원래 nullable인 필드를 강제 필수로 만들라는 뜻은 아니다.
5. **보유 어댑터는 사용하지 않는다.** 보유 목록, 소유 관계, 어댑터 선택·추천·변환 호환 판정·관련 API/폼/localStorage를 구현하지 않는다. 원본 스키마 보존을 위해 adapter 테이블·도메인·ORM은 남기되 비활성 참조 구조로만 둔다. 실제 충전 판정은 직접 연결만 한다.
6. SQLite 접근·설정·파일·ORM·DB 관련 스크립트는 모두 dal, 순수 업무 도메인은 cmn, SSR 페이지·폼·HTTP API·HTML/CSS/JS는 pl에 둔다.
7. 도메인 주도로 개발한다. 라우터는 업무 규칙과 SQL을 직접 실행하지 않는다. cmn의 모든 필드에 현실의 대상·단위·의미를 비전공자가 이해할 한국어 주석으로 단다.
8. 제공 ERD/DDL 기반 13테이블·65컬럼·키·관계·제약을 유지한다. PostgreSQL 전용 문법은 §13처럼 SQLite로 변환한다.
9. 학교 프로젝트 MVP에서 개인정보 저장을 금지하거나 가짜 데이터만 저장하도록 제한하지 않는다. 로그인·역할 권한·익명화·동의 흐름 등 별도 개인정보 관리 기능은 이번 구현의 선행 조건으로 추가하지 않는다.
10. 브라우저는 원본 프로필 저장소가 아니다. 재시작·다른 브라우저에서도 DB의 운전자·차량·멤버십을 조회한다. 선택한 ID와 검색 조건만 URL/폼에서 전달한다.
11. 원본에 없는 driver↔vehicle 소유/운행 관계와 driver↔adapter 관계를 만들지 않는다. 모든 등록 운전자·차량을 별도 목록에서 독립 선택한다. 특정 차량의 소유자라고 표시하지 않는다.
12. 이 문서가 이전 문서의 브라우저 전용 저장·개인정보 미수집·어댑터 기능·클라이언트 중심 렌더링 지침을 전부 대체한다.

### 1.3 범위

**MVP 필수:** DB 기반 운전자/차량/멤버십 CRUD, vehicle_accepts 관리, SSR 검색·목록·상세·이유, 지도 보조, 도착 시각 변경, 직접 커넥터 판정, 외부 길찾기, 키 없는 demo seed, venv 로컬 실행, 검증.

**제외:** 보유 어댑터 및 어댑터 판정, 로그인·회원가입, 멀티유저 권한 격리, 결제 실행, 실시간 고장·점유·대기, 로밍, 경로 최적화·트럭 라우팅, fleet 소유관계, SoC/주행거리 기반 도달 가능성, 자동 실데이터 수집, 배포·유료 가입. 도로 높이·축중·회전 반경의 법적/물리적 통행을 보장하지 않는다.

## 2. 고정 기술 구성과 새 프로젝트 초기화

| 영역 | 구현 기준 |
|---|---|
| 언어 | Python 3.12 이상 제안, 실제 환경에서 호환 검증 |
| 환경 | `python -m venv venv`, 프로젝트 venv의 Python/pip 사용 |
| HTTP | FastAPI + Uvicorn, 기본 127.0.0.1:8000 |
| SSR | Jinja2Templates + TemplateResponse, 페이지별 완성 HTML |
| UI | HTML/CSS, 보조 JavaScript ES modules, Leaflet 지도 |
| ORM | SQLAlchemy 2.x declarative ORM, 동기 Session |
| DB | 로컬 파일 `dal/data/pluggedin.db` |
| 폼/DTO | python-multipart, Pydantic; 폼은 HTML 응답, API는 JSON 응답 |
| 테스트 | pytest, HTTPX/TestClient, Python Playwright |
| 시간대 | zoneinfo + tzdata; 시간대 데이터의 실제 적용 결과 검증 |

requirements.txt에는 fastapi, uvicorn, SQLAlchemy, jinja2, python-multipart, tzdata를 포함한다. requirements-dev.txt는 `-r requirements.txt`와 pytest, httpx, playwright, pytest-playwright를 포함한다. agent가 설치·호환 검증한 정확한 버전을 고정해 제출한다. 프런트 Node 빌드와 별도 DB 서버를 필수로 도입하지 않는다.

pyproject.toml에 setuptools 기반 src layout을 설정해 `pip install -e .`로 `ca.uvic.ecs.csc501` 패키지를 설치한다. 필요한 각 디렉터리에 __init__.py를 둔다. README는 설치·초기화·실행·테스트·demo 시나리오·한계를 설명한다.

## 3. 필수 폴더 구조와 의존성

`ROOT=src/ca/uvic/ecs/csc501`로 약칭한다. 아래 구조 자체가 이전 참고 이미지의 cmn/dal/pl 책임을 재현한다.

```text
PluggedIn/
  venv/                         # 로컬 생성, git 제외
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  README.md
  AGENTS.md
  docs/PluggedIn_Development_Plan_AI_Agent.md
  src/ca/uvic/ecs/csc501/
    main.py                     # app 생성·라우터·의존성 조립
    cmn/
      organization.py
      site_owner.py
      operator.py
      network.py
      station.py
      connector_type.py
      port.py
      operating_period.py
      adapter.py                # 스키마 보존, 기능 미사용
      vehicle.py
      vehicle_accepts.py
      driver.py
      membership.py
      value_objects/            # Location, DailyTime
      contracts/                # Protocol·enum·읽기 모델
      services/                 # 네 항목 및 종합 판정
      application/              # CRUD·검색·상세 use case
    dal/
      config.properties
      settings.py
      database.py
      unit_of_work.py
      models/                   # 테이블마다 *_model.py, 총 13개
      mappers/                  # ORM ↔ cmn
      repositories/
      scripts/
        schema.sql              # §13 내용
        init_db.py
        seed_demo.py
        validate_db.py
      data/
        pluggedin.db
        station_metadata.json   # DDL에 없는 시간대·시간표 완전성·출처만
    pl/
      routes/
        pages.py
        driver_routes.py
        vehicle_routes.py
        membership_routes.py
        station_routes.py
        api_routes.py
      schemas.py                # Pydantic HTTP DTO
      dependencies.py            # use case 주입 인터페이스
      error_handlers.py
      templates/
        base.html
        index.html
        drivers/list.html
        drivers/form.html
        vehicles/list.html
        vehicles/form.html
        memberships/list.html
        memberships/form.html
        stations/list.html
        stations/detail.html
        errors/error.html
      static/
        css/app.css
        js/map.js
        js/forms.js
        vendor/
  tests/unit/
  tests/integration/
  tests/architecture/
  tests/e2e/
```

**의존성 규칙:** pl → cmn/application → cmn 도메인·repository Protocol. dal은 cmn Protocol을 구현한다. main.py가 dal 구현을 use case에 주입한다. cmn은 FastAPI/Pydantic/SQLAlchemy/sqlite3·파일 I/O를 import하지 않는다. pl은 dal·Session·SQL을 직접 import/사용하지 않는다. main에는 DB 연결 구현이나 SQL을 두지 않는다. static mount는 pl/static만 노출한다.

동기 Session을 쓰므로 DB 사용하는 FastAPI route는 `def`로 구현한다. 요청/작업당 Session 하나를 생성·종료하고 전역 공유하지 않는다. repository는 commit하지 않고 UoW가 flush→규칙 검사→commit/rollback을 책임진다. ORM 객체는 mapper로 순수 도메인/읽기 모델로 변환해 Session 밖에 전달한다.

## 4. 도메인·저장 책임과 DDD

### 4.1 업무 모델

| Aggregate/영역 | 책임 |
|---|---|
| Driver | 면허번호·이름·운송사 정보; 운전자별 멤버십 조회 |
| Vehicle | VIN·차량번호·사양 및 VehicleAccepts 연결 집합 |
| Membership | Driver와 Network 연결, 기간의 유효성 |
| Organization | 조직과 owner/operator/network 역할, 중복 가능한 역할과 최소 한 역할 |
| Station | 시설 정보, Ports, OperatingPeriods를 합친 조회 모델 |
| ConnectorType | 직접 연결 시 비교할 규격 |
| Adapter | 원본 테이블·모델 보존만, 현재 use case에서 참조 금지 |

Vehicle 저장과 vehicle_accepts 집합 교체는 같은 트랜잭션이다. 최소 하나의 수용 커넥터를 선택한다. Driver 삭제는 원본 FK대로 Membership을 함께 지운다. Vehicle 삭제는 VehicleAccepts만 함께 지우며 Driver/Membership을 지우지 않는다. 같은 운전자의 같은 네트워크 기간 중첩은 DDL이 금지하지 않으므로 임의로 금지하지 않는다. 동일 `(driver_id,network_id,start_date)` 중복은 거부한다.

### 4.2 값·필드·매핑

- 테이블마다 cmn의 별도 dataclass/entity 파일 및 dal/models의 별도 ORM 파일을 작성한다. 13테이블 65컬럼 전부 §14와 대응시킨다.
- 각 cmn 필드 바로 위 한국어 주석은 현실 의미·단위·None의 의미를 설명한다. “FK/PK”만 적은 주석은 불충분하다. 새로 추가한 DTO/값 객체 필드도 같은 기준으로 설명한다.
- 생성 전 surrogate ID는 `int | None`, DB에서 읽은 ID는 양수다. 역할 테이블 ID는 Organization ID를 공유한다.
- Python `Vehicle.vehicle_class`를 원본 DB 컬럼 `class`에 매핑한다. SQL 이름을 vehicle_class로 바꾸지 않는다.
- 좌표·출력은 Decimal을 쓰고 ORM Numeric과 변환한다. 입력은 좌표 6자리, 출력 1자리로 정규화한다. 문자열 길이는 도메인/DTO에서 검증한다. VIN은 정확히 17자, licence_number는 공백 제거 후 1–30자다. 이름 등 선택 문자열의 빈 입력은 None으로 저장한다.
- `DailyTime`은 자정부터의 초 0–86400이며 86400은 close_time에만 허용한다. DB는 HH:MM:SS의 8자리 TEXT. 기본 Python time/SQLAlchemy Time에 24:00을 넘기지 말고 custom TypeDecorator/mapper를 사용한다.
- Membership.is_active_on(local_date), OperatingPeriod.contains(local_datetime), Vehicle.accepts(connector_id) 같은 entity 책임을 구현한다. 여러 entity를 합치는 네 항목 판정은 domain service에서 수행한다.

```python
@dataclass(frozen=True)
class Driver:
    # 운전자 한 명을 서비스 안에서 구별하는 번호입니다. 면허번호 자체가 아닙니다.
    driver_id: int | None
    # 운전자의 면허번호입니다. 등록 폼에서 입력받아 DB에 저장하고 중복을 허용하지 않습니다.
    licence_number: str
    # 화면에서 운전자를 식별할 이름입니다. 입력하지 않았으면 None입니다.
    name: str | None
    # 운전자가 속한 운송사 이름입니다. 충전 네트워크 이름과는 다릅니다.
    carrier_name: str | None
```

### 4.3 내부 계약

```python
class DriverRepository(Protocol):
    def get(self, driver_id: int) -> Driver | None: ...
    def list(self) -> list[Driver]: ...
    def save(self, driver: Driver) -> Driver: ...
    def delete(self, driver_id: int) -> None: ...

def evaluate_station(station: StationSnapshot, vehicle: VehicleSnapshot,
                     memberships: list[Membership], arrival_at: datetime,
                     policy: EvaluationPolicy) -> EvaluationResult: ...
```

Vehicle/Membership/Station/Organization repository도 같은 책임으로 별도 Protocol을 정의한다. UoW 포트는 repositories와 commit/rollback을 제공한다. 평가 함수는 DB·파일·시스템 시계에 접근하지 않으며 호출자가 확정한 aware UTC datetime을 받는다. SSR과 JSON API 모두 같은 use case와 domain service를 호출한다.

## 5. 로컬 DB·스키마·보조 데이터

### 5.1 필수 저장 및 읽기

운전자·차량·수용 커넥터·멤버십은 반드시 실제 SQLite 행으로 저장한다. 선택 driver_id의 memberships를 repository로 조회하고 선택 vehicle_id의 Vehicle와 VehicleAccepts를 로딩한다. HTML hidden input이나 클라이언트 JSON에 실린 사양·멤버십은 진실의 원천으로 사용하지 않는다.

등록/수정 후 새로고침, 서버 재시작, 다른 브라우저에서 값이 유지되는지 검증한다. localStorage 전용 프로필, 개인정보 때문에 save를 무시하는 코드, 생성한 모델을 demo 읽기에만 쓰는 구현은 금지한다.

### 5.2 SQLite 변환 기준

§13 DDL은 원본의 13테이블·65컬럼·복합 AK·FK·삭제 동작·양수/요일/날짜/방향 제약·8개 인덱스를 포함한다. 역할 표는 WITHOUT ROWID여서 별도 ID를 자동 생성하지 않는다. 다른 PK는 SQLite INTEGER PRIMARY KEY로 자동 생성하며 PostgreSQL GENERATED ALWAYS의 명시 ID 거부까지 동일하게 보장하는 것은 아니다.

SQLite는 VARCHAR 길이·NUMERIC 정밀도를 원본 DB처럼 강제하지 않으므로 도메인·DTO 검증을 병행한다. INTEGER의 boolean은 0/1 CHECK와 ORM Boolean으로 매핑한다. 업무 CRUD는 SQLAlchemy ORM만 사용한다. raw SQL은 dal의 DDL 초기화·PRAGMA·스키마 검사에 한정한다.

각 연결에 PRAGMA foreign_keys=ON 및 busy_timeout을 적용한다. foreign_keys가 실제 1인지 연결마다 테스트한다. Session 예외는 rollback하고 항상 close한다. init_db는 기존 DB를 파괴하지 않는다. 앱 시작 시 create_all로 스키마를 몰래 대체하지 않는다.

### 5.3 스키마 밖 제약

원본 Organization ISA total 지연 트리거는 SQLite에 없으므로 UoW가 flush 후 모든 살아 있는 Organization의 역할을 검사하고 역할 없는 조직이면 commit을 거부한다. 생성·삭제·역할 이동 모두 검사한다. 직접 DB 도구로 쓰면 이 규칙을 우회할 수 있으므로 validate_db가 동일 규칙을 재검사한다.

완전한 aggregate는 Station의 Port/OperatingPeriod 각 1개 이상, Owner/Operator의 Station 1개 이상, Vehicle의 VehicleAccepts 1개 이상을 검증한다. 운전자/차량 UI의 차량 등록은 VehicleAccepts와 함께 저장한다. 운영시간 미상 demo 시설은 명시적 INCOMPLETE로 허용하고 UNKNOWN으로 표시한다. NOT NULL/FK/UNIQUE/CHECK 위반이나 역할 없는 Organization은 INCOMPLETE로도 허용하지 않는다.

### 5.4 시간대·시간표·출처 메타데이터

원본 13테이블에 없는 보조 필드만 dal/data/station_metadata.json에 둔다. 사용자/차량/멤버십 정보는 여기에 넣지 않는다. 형식은 다음과 같으며 키는 station_id 문자열이다.

```json
{
  "schemaVersion": 1,
  "stations": {
    "1": {
      "timezone": "America/Vancouver",
      "hoursCompleteness": "COMPLETE",
      "portsCompleteness": "COMPLETE",
      "aggregateCompleteness": "COMPLETE",
      "sourceLabel": "Local project demo data",
      "sourceUpdatedAt": null,
      "unconfirmedFields": []
    }
  }
}
```

dal이 DB와 metadata를 StationSnapshot으로 합친다. 파일이나 항목 누락은 관련 항목 UNKNOWN이다. hoursCompleteness와 portsCompleteness는 각각 COMPLETE/PARTIAL/UNKNOWN이다. 시간표가 COMPLETE일 때만 없는 요일을 휴무로 본다. portsCompleteness가 PARTIAL/UNKNOWN이면 알려진 직접 포트가 모두 실패해도 미확인 포트 후보를 남겨 UNKNOWN으로 집계한다. 그 후보에도 시설 공통 opening/access/payment를 적용하므로 공통 FAIL은 유지된다. INCOMPLETE 시설·일부 포트 목록을 완전 목록처럼 취급하지 않는다. sourceUpdatedAt=null이면 “갱신일 미상”이다. 로컬 수동/seed의 명시 bool은 확인값으로 사용하되 외부 원본 누락으로 DEFAULT만 적용된 필드는 unconfirmedFields에 넣어 판정에서 UNKNOWN으로 둔다. 포트 수량 미확인도 실제 1개로 주장하지 않는다.

metadata를 열고 쓰는 코드는 dal에만 존재한다. 원본 스키마를 보존하므로 시간대·출처 추가 컬럼이나 개인별 JSON 파일로 schema를 확장하지 않는다. 이번 MVP의 사용자 정보는 모두 SQL 테이블에서 관리한다.

## 6. SSR 화면과 페이지 동작 — 필수

### 6.1 렌더링 규칙

서버가 DB를 조회하고 use case·domain service를 실행한 뒤 Jinja2 context를 구성하여 **결과 본문이 이미 포함된 완성 HTML**을 반환한다. 폼 오류·목록·선택값·네 판정·이유·상세 표를 templates에서 렌더링한다. JS가 꺼져도 등록/수정/삭제·검색·목록·상세·판정·길찾기 링크가 사용 가능해야 한다. 지도 자체는 JS가 필요하므로 같은 결과의 SSR 목록을 항상 제공한다.

JS는 Leaflet 마커, 폼 UX, 위치 권한 보조에만 사용한다. 지도 데이터는 서버가 `<script type="application/json" id="map-data">`에 Jinja `tojson`으로 안전하게 삽입하고 map.js가 읽는다. 별도 fetch가 성공해야 결과가 나타나는 구조, SPA 라우팅, client-side template 엔진은 사용하지 않는다. 검색 조건을 바꾸면 HTML form GET으로 새 페이지를 렌더링한다.

TemplateResponse에는 request, template name, context를 명시한다. base.html은 공통 네비게이션·CSS·메시지·footer를 제공한다. HTML 텍스트는 autoescape하고 원문에 safe 필터를 적용하지 않는다. form mutation 성공은 303 redirect로 POST/Redirect/GET을 사용한다. 오류는 입력값·선택값을 유지한 SSR 폼과 field_errors를 400으로 반환한다. 삭제는 GET이 아니라 POST form으로 처리한다.

### 6.2 SSR 라우트

| Method | 경로 | 동작·템플릿 |
|---|---|---|
| GET | `/` | index.html: 설명, 등록 메뉴, driver/vehicle 선택·검색 폼 |
| GET | `/drivers` | 등록 운전자 SSR 목록 |
| GET | `/drivers/new` | driver form |
| POST | `/drivers` | 생성 후 /drivers로 303 |
| GET | `/drivers/{id}/edit` | DB 값으로 form 채움 |
| POST | `/drivers/{id}` | 수정 후 303 |
| POST | `/drivers/{id}/delete` | 삭제·멤버십 cascade 후 303 |
| GET/POST | `/vehicles/new`, `/vehicles` | GET new form / POST 생성; GET /vehicles는 목록 |
| GET/POST | `/vehicles/{id}/edit`, `/vehicles/{id}` | GET edit form / POST 수정 |
| POST | `/vehicles/{id}/delete` | vehicle_accepts cascade 후 303 |
| GET/POST | `/memberships/new`, `/memberships` | GET new form / POST 생성; GET /memberships는 목록·driver_id 필터 |
| GET/POST | `/memberships/{id}/edit`, `/memberships/{id}` | GET edit form / POST 수정 |
| POST | `/memberships/{id}/delete` | 해당 가입 행만 삭제 후 303 |
| GET | `/stations` | DB 조건으로 판정한 stations/list.html |
| GET | `/stations/{id}` | 같은 조건으로 stations/detail.html |

새/목록 경로는 동적 /{id} 경로와 충돌하지 않게 정의한다. 도메인별 CRUD는 이름만 있는 빈 화면이 아니라 실제 DB와 연결한다.

### 6.3 입력 폼

- Driver: licence_number 필수; name/carrier_name 선택. 목록에는 ID·이름·면허·운송사와 수정/삭제 링크.
- Vehicle: vin 필수 17자; licence_plate/make/model/vehicle_class/range_km/max_charge_kw 선택. accepted_connector_ids는 다중 선택, 최소 1개. 목록·편집에서 수용 커넥터가 보인다.
- Membership: driver_id/network_id/start_date 필수, end_date 선택. 네트워크 목록은 network 역할을 가진 organization만 표시한다. network_id는 organization_id와 같은 값이다.
- 선택 필드도 제출하면 모두 DB에 보존한다. 수정 폼은 None을 빈 입력으로, 숫자 0은 잘못된 값으로 처리한다. 부분 제출 PATCH와 달리 SSR edit POST는 전체 form 교체다.

### 6.4 검색 조건·context

`driver_id`, `vehicle_id`는 필수이며 driver/vehicle를 독립 선택한다. `arrival_at`은 offset/Z를 포함하는 ISO aware datetime, 빈 값이면 현재 시각. SSR 폼은 기본 offset 포함 문자열을 보여주고 옆에 시간대 설명을 붙인다. timezone 없는 datetime-local을 브라우저 시간대로 조용히 해석하지 않는다.

선택 옵션: west/south/east/north bbox(기본 -123.50/48.35/-123.20/48.60), status(ALL/AVAILABLE/NEEDS_REVIEW/UNAVAILABLE). 범위는 west<east, south<north. 입력된 ID가 없으면 404, 조건이 잘못되면 400 SSR 오류다. 결과가 없으면 조건 유지·0개 안내를 렌더링한다.

현재 시각은 요청당 한 번 확정하고 결과 링크·hidden form에 그 arrival_at을 그대로 넣는다. 상세는 같은 instant로 평가하며 서버 현재 시각으로 보정하지 않는다. 과거 instant도 동일 시나리오 재현용으로 허용한다. 새로운 “지금 검색”은 arrival_at을 비워 새 시각을 만든다. HTML 응답은 평가 시각과 도착 시각을 표시한다.

list context: drivers, vehicles, selected_driver, selected_vehicle, filters, evaluation_at, arrival_at, results, counts, map_data, errors. detail context: 동일 선택·시각, station, ports, operating_periods, organizations, checks, overall_status, compatible_port_ids, power_limit_kw, reasons, source, disclaimer. 도메인 결과를 context로 변환하는 책임은 pl에 있다.

## 7. 네 가지 판정 규칙

### 7.1 공통 상태

CheckStatus=PASS/FAIL/UNKNOWN, OverallStatus=AVAILABLE/UNAVAILABLE/NEEDS_REVIEW. 항목 AND는 FAIL 우선, 다음 UNKNOWN, 모두 PASS이면 AVAILABLE. 여러 실제 직접 연결 포트의 OR는 AVAILABLE 우선, 다음 NEEDS_REVIEW, 전부 확정 실패면 UNAVAILABLE이다. 선택 포트의 플러그와 다른 포트의 장점을 합쳐 통과시키지 않는다. 포트 정보가 부족해도 시설 공통 폐쇄·접근 금지 FAIL은 유지한다.

CheckResult는 status, reasons(코드·쉬운 문구), evidence(사용한 DB 값/시간표)를 갖는다. EvaluationResult는 station_id, driver_id, vehicle_id, arrival_at, checks 4개, overall_status, compatible_port_ids, selected_port_id, power_limit_kw, warnings를 갖는다. 정확한 Python 타입은 cmn/contracts에 정의하고 SSR/JSON이 공유한다. ID를 제외한 개인정보를 결과 URL에 직접 넣지 않는다.

### 7.2 opening

station.status를 ACTIVE/INACTIVE/PLANNED/TEMPORARILY_CLOSED/UNKNOWN으로 정규화한다. ACTIVE와 운영시간 PASS가 모두 있어야 opening PASS다. 영구 폐쇄 INACTIVE는 FAIL, 기간을 모르는 일시 폐쇄·상태 미상은 UNKNOWN이다. 시간표 자체가 명시적으로 닫혔으면 상태 미상이어도 FAIL이다.

충전소 metadata의 IANA timezone으로 arrival_at을 변환한다. zone 미상이면 UNKNOWN. 구간은 [open,close)로 개점 정각 포함·폐점 정각 제외. Mon 22–Tue 06은 Mon 22:00:00–24:00:00 + Tue 00:00:00–06:00:00 두 행이다. 24/7은 일주일 7개 요일의 00:00:00–24:00:00. 일요일·연말 경계도 날짜 연산으로 처리한다. COMPLETE 시간표의 없는 요일은 휴무, PARTIAL/UNKNOWN 또는 행 없음은 UNKNOWN이다. 2026 이후 BC의 시간대 변경은 최신 tzdata 결과를 사용하며 매년 11월 -08로 복귀한다고 하드코딩하지 않는다.

### 7.3 access

access_restriction을 공백·대소문자 정규화한다. public은 자격 PASS, no public access/closed to public은 FAIL, customers only/fleet only/private/빈 값/미해석 조건은 UNKNOWN이다. 운송사 이름만 보고 플릿 승인 여부를 추측하지 않는다.

차량 분류는 CAR, VAN, MEDIUM_TRUCK, HEAVY_TRUCK으로 한다. station.max_vehicle_class는 같은 네 값 또는 ALL만 지원한다. UI 분류의 허용 순서는 CAR<VAN<MEDIUM_TRUCK<HEAVY_TRUCK으로 명시하며 법정 중량 등급 비교라고 주장하지 않는다. ALL은 명시 제한 없음이다. 선택 차량 class가 제한을 초과하면 FAIL, 비교값이 없거나 미지원이면 UNKNOWN이다. 중대형 트럭은 has_truck_parking=true만으로 충전 진입을 확정하지 않으므로 추가 물리 정보가 없는 현재 모델에서는 물리 조건을 UNKNOWN으로 평가한다. access는 자격·등급·해당 차량에 필요한 물리 조건의 AND다. 따라서 다른 조건을 통과해도 중대형 트럭의 access는 UNKNOWN이며 TRUCK_CLEARANCE_UNKNOWN을 표시한다. CAR/VAN은 명시된 등급 범위까지만 평가하고 전체 실제 여유 공간을 보장하지 않는다.

### 7.4 connector — 직접 연결만

vehicle_accepts에서 선택 vehicle_id의 수용 규격 ID들을 조회한다. port.connector_type_id가 수용 집합에 있고 전류 유형이 검증 가능한 조합이면 직접 연결 후보다. J1772=AC, CCS1=DC, CHAdeMO=DC만 기본 검증 조합으로 정의한다. current_type=null, 모호한 규격, NACS/TESLA처럼 차종·시설 추가 조건을 이 모델로 검증할 수 없는 조합은 UNKNOWN이다. 미지원 변환을 adapter 테이블에서 찾아 통과시키지 않는다.

완전한 포트 목록에서 수용 규격과 일치하는 직접 포트가 하나도 없으면 FAIL. 수용 정보·포트 목록 자체가 없거나 불완전하면 UNKNOWN. 하나라도 검증된 직접 연결 포트가 있으면 PASS. 후보 선택은 알려진 출력 높은 순, 마지막 port_id 오름차순으로 결정한다.

출력 상한은 min(port.power_kw,vehicle.max_charge_kw). 둘 다 알려졌을 때 숫자, 하나라도 없으면 null과 “출력 미상”이다. 출력 미상 자체는 플러그 호환을 실패시키지 않는다. connector_type.max_power_kw나 quantity를 실제 포트 출력에 곱하지 않는다.

### 7.5 payment

선택 driver_id의 Membership을 DB에서 로딩한다. station.network_id와 같은 network_id이고 충전소 현지 날짜가 start_date≤arrival_date≤end_date인 멤버십이 있으면 PASS. end_date=None은 종료일 미지정이다. 동일 조직의 owner/operator 역할과 network 역할을 혼동하지 않는다.

확인된 accepts_guest_payment=true여도 PASS다. 같은 네트워크 멤버십이 없고 guest=false이면 FAIL. network_id가 없고 guest=false, 또는 guest 원본 값이 미확인이면 UNKNOWN이다. guest=true면 네트워크 미상이어도 PASS다. 로밍·실제 잔액·카드 인증은 평가하지 않는다. 선택 운전자를 바꾸면 가입 내역을 다시 DB에서 읽는다.

### 7.6 필수 이유 코드·안내

OPEN/CLOSED/HOURS_UNKNOWN/TIMEZONE_UNKNOWN/FACILITY_STATUS_UNKNOWN,
ACCESS_PUBLIC/ACCESS_DENIED/ACCESS_RESTRICTED_UNKNOWN/VEHICLE_TOO_LARGE/VEHICLE_CLASS_UNKNOWN/TRUCK_CLEARANCE_UNKNOWN,
DIRECT_COMPATIBLE/DIRECT_INCOMPATIBLE/CONNECTOR_UNKNOWN/PORTS_UNKNOWN,
MEMBERSHIP_ACCEPTED/GUEST_PAYMENT_ACCEPTED/NO_PAYMENT_OPTION/PAYMENT_UNKNOWN,
POWER_UNKNOWN을 상수 enum으로 고정한다.

화면에는 “공개·등록 데이터 기준의 추정”, “실시간 고장·대기 미반영”, “도로 통행·전체 차량 여유 공간 미검증”, “출력은 실제 속도 보장이 아님”을 표시한다. 색만 쓰지 않고 상태 텍스트와 이유를 함께 SSR로 제공한다.

## 8. JSON API 계약 — SSR와 같은 use case

JSON API는 테스트·API 개발 결과 확인용이며 SSR 화면을 JSON fetch 의존 구조로 만들지 않는다. 내부 Python은 snake_case, JSON도 이번 버전에서는 **snake_case**로 통일한다. 이전 camelCase·profile·ownedAdapterIds 계약은 사용하지 않는다.

| Method | 경로 | 계약 |
|---|---|---|
| GET/POST | `/api/v1/drivers` | 목록/생성 |
| GET/PUT/DELETE | `/api/v1/drivers/{id}` | 조회/전체 수정/삭제 |
| GET/POST | `/api/v1/vehicles` | 수용 규격 포함 목록/생성 |
| GET/PUT/DELETE | `/api/v1/vehicles/{id}` | 조회/전체 수정/삭제 |
| GET/POST | `/api/v1/memberships` | 목록(driver_id 선택 필터)/생성 |
| GET/PUT/DELETE | `/api/v1/memberships/{id}` | 조회/전체 수정/삭제 |
| GET | `/api/v1/catalog` | connectors 및 network 역할 organization 목록 |
| POST | `/api/v1/stations/search` | driver_id,vehicle_id,arrival_at,bbox로 DB 기반 평가 |
| POST | `/api/v1/stations/{id}/evaluate` | driver_id,vehicle_id,arrival_at로 같은 평가 상세 |
| GET | `/api/v1/health` | DB 연결·schema 준비 여부, 준비 안 됨 503 |

create 성공 201, get/put 200, delete 204. 목록은 id 오름차순의 JSON 배열. Driver input={licence_number,name,carrier_name}; Vehicle input={vin,licence_plate,make,model,vehicle_class,range_km,max_charge_kw,accepted_connector_ids}; Membership input={driver_id,network_id,start_date,end_date}. NOT NULL key 및 accepted_connector_ids는 필수, nullable key는 생략하면 None. PUT은 같은 전체 필드 계약으로 교체한다. 응답은 해당 입력 필드에 생성된 *_id를 추가한다. Vehicle 응답 accepted_connector_ids는 중복 없는 정렬 목록이다.

```json
{
  "driver_id": 1,
  "vehicle_id": 1,
  "arrival_at": "2026-10-26T19:00:00Z",
  "bbox": {"west": -123.5, "south": 48.35, "east": -123.2, "north": 48.6}
}
```

arrival_at=null/생략이면 요청 시 현재, 명시 시 그대로 사용. bbox는 search 필수이고 상세 evaluate에는 없다. 결과는 `{driver_id,vehicle_id,arrival_at,results:[EvaluationResult],counts:{AVAILABLE,NEEDS_REVIEW,UNAVAILABLE}}`. 상세는 단일 EvaluationResult에 station/ports/periods/organizations/source를 추가한다. Decimal은 경계에서 숫자로 직렬화하고 날짜는 ISO, datetime은 offset/Z로 직렬화한다. API 입력에 운전자 이름·차량 사양·멤버십 목록을 복사해 보내 DB 로딩을 우회하지 않는다.

오류 envelope: `{error:{code,message,field_errors}}`. 400 입력·날짜·enum·수용 규격 오류, 404 없는 ID, 409 VIN/면허/복합키 중복·FK 참조 삭제 충돌, 503 DB 미준비, 500 예상 밖 오류. FastAPI validation 기본 422는 명시적 handler로 400 envelope/SSR field_errors에 맞춘다. 저장 실패 시 rollback하고 원본 값을 유지한다. nullable 공백은 None으로 정규화하지만 VIN·면허 공백은 필수 오류다. HTML 오류는 JSON 대신 HTML로 반환한다.

## 9. 자체 완결 demo 데이터와 시연

외부 API 키 없이 아래 합성 자료를 ORM seed로 생성한다. 이 문서의 정답은 실제 시설 현황을 뜻하지 않는다. id를 명시하는 seed가 SQLite에서 허용됨을 이용하되 일반 생성 API는 client ID를 받지 않는다. seed는 하나의 UoW에서 전체 관계를 만들고 검사한다.

| 테이블/ID | 값 |
|---|---|
| organization 1 | name=Demo Charging Company, website=null |
| site_owner 1 | business_type=Demo charging site |
| operator 1 | support_phone=000-000-0000 |
| network 1 | payment_method=Membership or guest |
| organization/network 2 | name=Demo Other Network; network 역할만, payment_method=Membership |
| connector_type 1/2 | CCS1/CHAdeMO, max_power_kw=null |
| driver 1 | licence_number=DEMO-LIC-001, name=Mina, carrier_name=Demo Delivery |
| driver 2 | licence_number=DEMO-LIC-002, name=Jin, carrier_name=null |
| vehicle 1 | vin=DEMO0000000000001 (17자), licence_plate=DEMO-01, make=Demo, model=Van, class=VAN, range_km=250, max_charge_kw=100 |
| vehicle_accepts 1 | vehicle_id=1,connector_type_id=1 |
| membership 1 | driver_id=1,network_id=1,start_date=2026-01-01,end_date=null |
| membership 2 | driver_id=2,network_id=2,start_date=2026-01-01,end_date=null |

모든 시설 owner_id/operator_id/network_id=1, city=Victoria, province=BC, status=ACTIVE, access_restriction=public, max_vehicle_class=VAN, has_truck_parking=false, guest=false를 기본값으로 둔다. 각 시설에 number=1/quantity=1/current_type=DC/power_kw=150 포트를 하나씩 만든다.

| station_id | 이름·좌표 | 변경 조건 | 운영시간 |
|---|---|---|---|
| 1 | Demo A,48.46,-123.31 | CCS1 | 매일 00:00:00–24:00:00 |
| 2 | Demo B,48.47,-123.32 | CCS1 | Mon–Fri 09:00:00–17:00:00 |
| 3 | Demo C,48.48,-123.33 | CHAdeMO | 매일 00:00:00–24:00:00 |
| 4 | Demo D,48.49,-123.34 | CCS1, 시간표 미상 | 행 없음, INCOMPLETE |
| 5 | Demo E,48.50,-123.35 | CCS1,guest=true | 매일 00:00:00–24:00:00 |

port_id는 station_id와 동일하게 1–5로 정한다. metadata는 1–5 모두 America/Vancouver 및 portsCompleteness=COMPLETE, D만 hoursCompleteness=UNKNOWN/aggregateCompleteness=INCOMPLETE, 나머지 COMPLETE. sourceLabel은 Local project demo data, sourceUpdatedAt=null, unconfirmedFields=[]로 둔다. adapter는 빈 테이블이어도 정상이다.

2026-10-26T19:00:00Z(현지 월요일 12시)의 Mina+Vehicle1: A AVAILABLE, B AVAILABLE, C UNAVAILABLE, D NEEDS_REVIEW, E AVAILABLE. 2026-10-27T05:00:00Z(월 22시)에서 B는 CLOSED다. Jin+Vehicle1은 A 결제 FAIL, E guest PASS다. Jin에게 network1 멤버십을 추가하면 A가 AVAILABLE로 바뀌고 삭제하면 다시 FAIL이다. 차량 수용 커넥터를 CHAdeMO만으로 수정하면 C는 직접 호환되고 A는 불일치한다.

지도 타일이 실패하거나 JS가 꺼져도 이 시연을 SSR 목록·상세에서 수행할 수 있어야 한다. 타일 공급자 attribution과 고정 버전 Leaflet 자산을 기록한다. 외부 길찾기는 사용자가 누르는 허용된 공급자 링크에 목적지 좌표만 넣는다.

## 10. 실행 명령과 전달물

구현 agent는 다음 명령을 실제 제공하고 실행 결과를 기록한다. 아래는 이 문서를 따라 생성될 MVP의 명령 계약이며 문서 작성 시 구현이 이미 완료됐다는 뜻은 아니다.

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pip install -e .
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.init_db
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.seed_demo
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.validate_db
.\venv\Scripts\python.exe -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
```

Linux/macOS:

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements-dev.txt
venv/bin/python -m pip install -e .
venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.init_db
venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.seed_demo
venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.validate_db
venv/bin/python -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
```

페이지 `/`, API 문서 `/docs`를 확인한다. config.properties는 `[sqlite]` 섹션의 database_path=data/pluggedin.db, foreign_keys=true, busy_timeout_ms=5000을 포함하며 dal 디렉터리를 기준으로 resolve한다. DB 경로가 dal 경계를 벗어나면 설정 오류다. init_db는 새 파일만 생성하고 기존이면 schema를 검사한다. seed_demo는 demo 행이 이미 동일하면 중복 생성하지 않는다. 기존 수정 데이터와 충돌하면 덮어쓰지 않고 알려준다. 재실행·서버 재시작은 사용자 CRUD 데이터를 보존한다.

```bash
venv/bin/python -m pytest tests/unit tests/integration tests/architecture
venv/bin/python -m playwright install chromium
venv/bin/python -m pytest tests/e2e
```

테스트는 임시 dal 디렉터리의 DB로 격리한다. README는 위 Windows/Linux 명령, sample URL, driver/vehicle 독립 선택, 저장 범위, SSR 방식, 어댑터 제외, SQLite 트리거 변환·한계를 설명한다. schema.sql과 ORM이 일치해야 한다. 프로젝트 루트·DB를 웹 정적 폴더로 노출하지 않는다. 출력물은 소스·의존성 파일·스키마·seed·테스트·문서이며 venv 자체는 전달/버전 관리에서 제외한다.

## 11. 수용 테스트와 완료 조건

| ID | 검증 | 기대 |
|---|---|---|
| V01 | venv에서 설치·패키지 실행 | Python 프로젝트로 실행, 별도 DB 서버 불필요 |
| V02 | cmn/dal/pl 및 의존성 검사 | 13 도메인, ORM/DB는 dal, UI는 pl, main은 조립 |
| V03 | 원본 컬럼·주석 대조 | §13의 13테이블/65컬럼 전부 §14 도메인 필드와 대응 |
| V04 | FK 새 연결 2개 검사 | 각각 PRAGMA foreign_keys=1 |
| V05 | 좌표·면허·VIN·복합 AK 중복 | DB 거부·API409·SSR 오류, 기존 행 보존 |
| V06 | FK/CHECK/삭제 동작 | 원본 cascade 및 참조 제한 유지 |
| V07 | Organization+역할 생성/마지막 역할 삭제 | 같은 UoW 생성 성공, 역할 없는 commit 실패·rollback |
| V08 | 24:00 저장·ORM 왕복 | close=24:00 허용, 24:01/역순/open=24 거부 |
| V09 | Driver 전체 필드 생성·수정 | 면허/이름/운송사 DB 저장, SSR 재조회 일치 |
| V10 | Vehicle 전체 필드·수용 규격 저장 | 8컬럼+연결 테이블 DB 반영, 편집 폼 복원 |
| V11 | Membership 기간·네트워크 저장 | end<start 거부, null 종료일 허용 |
| V12 | 서버 재시작·다른 브라우저 | 같은 DB 데이터 유지, localStorage 불필요 |
| V13 | Driver/Vehicle 삭제 | Membership/VehicleAccepts 각각 cascade |
| V14 | vehicle_accepts 실패 포함 수정 | 차량·연결 전체 rollback, 반쪽 저장 없음 |
| V15 | JS 비활성 브라우저 | CRUD/검색/결과본문/상세/이유/링크 동작 |
| V16 | SSR HTML 원문 검사 | API fetch 전 이미 이름·상태·이유·폼 값 존재 |
| V17 | POST form 성공/오류 | 성공303, 오류400 HTML·값/선택 유지 |
| V18 | 지도 타일 실패 | SSR 목록·판정 계속 사용 가능 |
| V19 | 개점/폐점 정각 | 개점 PASS, 폐점 FAIL |
| V20 | Mon22–Tue06·Sun22–Mon06 | 날짜별 분할 후 새벽 PASS·06시 FAIL |
| V21 | 시간표 없음·PARTIAL·미상 시간대 | UNKNOWN, 가짜 시간표 생성 없음 |
| V22 | 상태 UNKNOWN+열린/닫힌 시간표 | UNKNOWN/FAIL |
| V23 | 같은 arrival_at 지도→상세 | 폐점 경계가 지나도 같은 instant 결과 |
| V24 | BC 2026-11-01/12-01 | Vancouver -07 적용, 구식 DST 하드코딩 없음 |
| V25 | 직접 CCS1/DC와 다른 규격 | 일치 PASS, 완전 목록 불일치 FAIL |
| V26 | 미상 전류·미검증 NACS | UNKNOWN; adapter 테이블로 우회하지 않음 |
| V27 | adapter ownership 검색 | 폼·API·localStorage·도메인 판정에 존재하지 않음 |
| V28 | 멤버십 시작/종료 날짜 포함 | 두 경계일 PASS, 만료 다음날 FAIL |
| V29 | 다른 운전자·다른 네트워크 | 실제 선택 driver의 DB 멤버십만 사용 |
| V30 | guest=true / network null+guest=false | PASS / UNKNOWN |
| V31 | 3^4=81개 항목 조합 | FAIL 우선→UNKNOWN→전부 PASS |
| V32 | 여러 직접 포트 및 부분 목록 | 포트 OR; 정보 부족이 시설 공통 FAIL을 지우지 않음 |
| V33 | fleet/customer 제한·운송사 이름 | 승인 추측 없이 UNKNOWN |
| V34 | 차량 제한 초과·트럭 주차만 있음 | FAIL / 물리 조건 UNKNOWN |
| V35 | 출력150·차량100 / 차량출력미상 | 100 / null; 호환성과 별도 |
| V36 | 같은 좌표의 별도 시설 | UNIQUE 유지, 좌표 조작·자동 병합 없음 |
| V37 | HTML 원문·사용자 입력 script | escape되어 실행 안 됨 |
| V38 | API 없는 ID/잘못된 입력/중복 | 404/400/409의 일관된 envelope |
| V39 | demo 초기화·seed 재실행 | 동일 seed 중복 없음, 수정 데이터 덮어쓰기 없음 |
| V40 | Mina/Jin CRUD→검색 시연 | §9의 결과 및 멤버십 변경에 따른 실제 재판정 |

완료는 V01–V40과 실제 venv 실행·브라우저 시연·SSR 무JS 테스트로 증명한다. 모델/테이블만 만들고 입력 저장을 막거나 JS로 모든 본문을 그리면 실패다. 테스트 대상은 코드 자체를 반복하는 무의미한 테스트가 아니라 저장·관계·업무 규칙·HTTP·사용자 흐름이다. 미실행 검증은 통과로 보고하지 않는다.

## 12. 구현 작업 순서와 agent 인계

| Task | 선행 | 파일·결과 | 검증 |
|---|---|---|---|
| T00 환경·구조 | 없음 | pyproject/requirements/venv 설명, ROOT/main, 패키지·폴더 | V01/V02 |
| T01 도메인 | T00 | cmn 13 entity, 값 객체, Protocol·결과 타입; §14 주석 | V03, 순수 unit |
| T02 DB·ORM | T01 | dal schema/config/engine/13 ORM/mapper/repository/UoW | V04–V08/V36 |
| T03 CRUD use case | T02 | cmn/application Driver/Vehicle/Membership 생성·수정·삭제·조회 | V09–V14 |
| T04 demo | T02 | dal init/seed/validate 및 station_metadata | V21/V39 |
| T05 판정 | T01 | cmn/services opening/access/connector/payment/aggregate | V19–V35 |
| T06 JSON API | T03/T05 | pl API·DTO·오류 처리, main 의존성 주입 | V29/V38 |
| T07 SSR CRUD | T03 | pl templates·GET/POST routes·PRG | V09–V17 |
| T08 SSR 검색·상세 | T04/T05/T07 | 서버 평가 context·HTML 결과·링크 | V15/V16/V23/V40 |
| T09 지도·스타일 | T08 | pl/static CSS·Leaflet·map-data·모바일·범례 | V18/V37 |
| T10 통합·인계 | T06/T09 | tests·README·실제 실행 결과·제약 | V01–V40 |

각 작업은 관련 테스트 작성→기대 실패 확인→최소 구현→테스트 실행→작업 보고 순서다. 환경·문서 작업은 import·실행·구조 검사로 검증한다. 업무 규칙과 저장 조건을 바꾸면 이 문서·테스트·use case·SSR·API를 함께 갱신한다. 새 작업마다 schema를 다시 설계하지 않는다.

**복사해서 쓸 agent 지시:**

```text
이 MD 하나를 기준으로 새 PluggedIn 프로젝트와 실행 가능한 MVP를 만들어라.
외부 첨부를 다시 요청하지 말고 §13 SQLite DDL, §14 65필드 사전,
§3 폴더 구조, §6 SSR 계약, §8 API, §9 demo를 구현 기준으로 삼아라.
FastAPI/Jinja2 SSR + HTML/CSS/JS + venv + SQLAlchemy ORM + 로컬 SQLite를 써라.
운전자·차량·수용 커넥터·멤버십 및 식별 필드를 실제 DB에 저장·CRUD하라.
보유 어댑터와 변환 기능은 만들지 말고 adapter 테이블/모델만 보존하라.
cmn/dal/pl 책임을 지키고 모든 도메인 필드에 쉬운 한국어 주석을 달아라.
페이지 결과를 서버에서 완성하고 JS가 없어도 주요 흐름이 동작하게 하라.
T00–T10을 의존 순서로 진행해 V01–V40을 검증하라.
완료 시 생성 파일, 실행 방법, 실제 테스트 결과, 남은 한계를 보고하라.
계획 재작성·빈 함수·정적 목업을 완료 산출물로 대신하지 마라.
```

### 참고·검증 범위

원본 ERD/SQL의 구조는 아래에 통합했으므로 실행 agent가 원본 첨부를 볼 필요 없다. 학교 프로젝트 최종 지시가 과거 정책보다 우선한다. 실제 충전소·제조사 어댑터·실시간 상태는 이번 문서에서 검증하지 않았으며 합성 seed를 실제 현황처럼 소개하지 않는다.

SSR 구현 참고(2026-10-26 확인): https://fastapi.tiangolo.com/advanced/templates/ . SQLite ORM 참고: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html . 시간대 참고: https://www.iana.org/time-zones . 링크는 라이브러리 사용 참고이며 업무 요구를 채우기 위해 별도 자료를 찾아야 하는 의존성은 아니다.

## 13. 내장 SQLite DDL — dal/scripts/schema.sql로 저장

아래 블록이 실행 가능한 스키마 전체다. 원본 PostgreSQL 함수/constraint trigger는 §5.3의 UoW 검증으로 옮겼다. 추가 clock CHECK는 SQLite TEXT의 유효 형식을 보장한다. ORM은 이 DDL의 컬럼·키·제약·기본값과 일치해야 한다.

```sql
PRAGMA foreign_keys=ON;

-- =====================================================================
-- PluggedIn — logical (relational) schema, SQLite adaptation
-- Derived from the MVP acyclic ERD (Chen + crow's foot).
-- Key policy: every table has a generated surrogate ID as PRIMARY KEY;
--             the ERD key (natural key / partial key) is kept as a
--             NOT NULL UNIQUE alternate key (AK).
-- ISA subclasses share the superclass ID (PK = FK to organization).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Organization hierarchy  (ISA: overlapping, total)
-- ---------------------------------------------------------------------
CREATE TABLE organization (
    organization_id   INTEGER PRIMARY KEY,
    name              VARCHAR(200) NOT NULL,
    website           VARCHAR(300),
    CONSTRAINT ak_organization_name UNIQUE (name)
);

-- Overlapping: one organization may appear in several subclass tables.
CREATE TABLE site_owner (
    organization_id   INTEGER NOT NULL PRIMARY KEY
                      REFERENCES organization (organization_id) ON DELETE CASCADE,
    business_type     VARCHAR(100)
) WITHOUT ROWID;

CREATE TABLE operator (
    organization_id   INTEGER NOT NULL PRIMARY KEY
                      REFERENCES organization (organization_id) ON DELETE CASCADE,
    support_phone     VARCHAR(30)
) WITHOUT ROWID;

CREATE TABLE network (
    organization_id   INTEGER NOT NULL PRIMARY KEY
                      REFERENCES organization (organization_id) ON DELETE CASCADE,
    payment_method    VARCHAR(200)
) WITHOUT ROWID;

-- ---------------------------------------------------------------------
-- Station  (OwnedBy 1:N, OperatedBy 1:N, ServedBy 0..1:N as FKs)
-- ---------------------------------------------------------------------
CREATE TABLE station (
    station_id            INTEGER PRIMARY KEY,
    latitude              NUMERIC(9,6) NOT NULL CHECK (latitude  BETWEEN -90  AND 90),
    longitude             NUMERIC(9,6) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    name                  VARCHAR(200),
    street                VARCHAR(200),          -- Address (composite) flattened
    city                  VARCHAR(100),
    province              VARCHAR(50),
    status                VARCHAR(50),
    access_restriction    VARCHAR(100),          -- e.g. public, fleet only, customers only
    accepts_guest_payment INTEGER NOT NULL DEFAULT 0 CHECK (accepts_guest_payment IN (0,1)),
    max_vehicle_class     VARCHAR(30),
    has_truck_parking     INTEGER NOT NULL DEFAULT 0 CHECK (has_truck_parking IN (0,1)),
    owner_id              INTEGER NOT NULL REFERENCES site_owner (organization_id),  -- OwnedBy  (1,1)
    operator_id           INTEGER NOT NULL REFERENCES operator   (organization_id),  -- OperatedBy (1,1)
    network_id            INTEGER          REFERENCES network    (organization_id),  -- ServedBy (0,1)
    CONSTRAINT ak_station_location UNIQUE (latitude, longitude)   -- ERD key: Location
);

-- ---------------------------------------------------------------------
-- Weak entities (identifying relationships Has / OpenDuring)
-- ---------------------------------------------------------------------
CREATE TABLE connector_type (
    connector_type_id INTEGER PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    max_power_kw      NUMERIC(6,1) CHECK (max_power_kw > 0),
    CONSTRAINT ak_connector_type_name UNIQUE (name)
);

CREATE TABLE port (
    port_id           INTEGER PRIMARY KEY,
    station_id        INTEGER NOT NULL REFERENCES station (station_id) ON DELETE CASCADE,  -- Has
    number            SMALLINT NOT NULL CHECK (number > 0),                                -- partial key
    connector_type_id INTEGER NOT NULL REFERENCES connector_type (connector_type_id),      -- HasType (1,1)
    power_kw          NUMERIC(6,1) CHECK (power_kw > 0),
    current_type      VARCHAR(5)  CHECK (current_type IN ('AC', 'DC')),
    quantity          SMALLINT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    CONSTRAINT ak_port UNIQUE (station_id, number)          -- owner key + partial key
);

CREATE TABLE operating_period (
    operating_period_id INTEGER PRIMARY KEY,
    station_id          INTEGER NOT NULL REFERENCES station (station_id) ON DELETE CASCADE,  -- OpenDuring
    day                 VARCHAR(3) NOT NULL
                        CHECK (day IN ('Mon','Tue','Wed','Thu','Fri','Sat','Sun')),        -- partial key
    open_time           TEXT NOT NULL,                                                       -- partial key
    close_time          TEXT NOT NULL,      -- 24:00 allowed for "until midnight"
    CONSTRAINT ak_operating_period UNIQUE (station_id, day, open_time),
    CONSTRAINT ck_operating_period_order CHECK (close_time > open_time),
    CONSTRAINT ck_open_clock CHECK (
      length(open_time)=8 AND
      open_time GLOB '[0-2][0-9]:[0-5][0-9]:[0-5][0-9]' AND open_time<'24:00:00'),
    CONSTRAINT ck_close_clock CHECK (
      close_time='24:00:00' OR (length(close_time)=8 AND
      close_time GLOB '[0-2][0-9]:[0-5][0-9]:[0-5][0-9]' AND close_time<'24:00:00'))
);

-- ---------------------------------------------------------------------
-- Adapter  (ConvertsFrom / ConvertsTo: each adapter has exactly one of each)
-- ---------------------------------------------------------------------
CREATE TABLE adapter (
    adapter_id             INTEGER PRIMARY KEY,
    model                  VARCHAR(100) NOT NULL,
    manufacturer           VARCHAR(100),
    max_power_kw           NUMERIC(6,1) CHECK (max_power_kw > 0),
    from_connector_type_id INTEGER NOT NULL REFERENCES connector_type (connector_type_id), -- ConvertsFrom (plug side)
    to_connector_type_id   INTEGER NOT NULL REFERENCES connector_type (connector_type_id), -- ConvertsTo  (inlet side)
    CONSTRAINT ak_adapter_model UNIQUE (model),
    CONSTRAINT ck_adapter_direction CHECK (from_connector_type_id <> to_connector_type_id)
);

-- ---------------------------------------------------------------------
-- Vehicle and Accepts (M:N)
-- ---------------------------------------------------------------------
CREATE TABLE vehicle (
    vehicle_id      INTEGER PRIMARY KEY,
    vin             CHAR(17) NOT NULL,
    licence_plate   VARCHAR(15),
    make            VARCHAR(50),
    model           VARCHAR(50),
    class           VARCHAR(30),
    range_km        INTEGER CHECK (range_km > 0),
    max_charge_kw   NUMERIC(6,1) CHECK (max_charge_kw > 0),
    CONSTRAINT ak_vehicle_vin UNIQUE (vin)
);

CREATE TABLE vehicle_accepts (
    vehicle_accepts_id INTEGER PRIMARY KEY,
    vehicle_id         INTEGER NOT NULL REFERENCES vehicle (vehicle_id) ON DELETE CASCADE,
    connector_type_id  INTEGER NOT NULL REFERENCES connector_type (connector_type_id),
    CONSTRAINT ak_vehicle_accepts UNIQUE (vehicle_id, connector_type_id)
);

-- ---------------------------------------------------------------------
-- Driver and MemberOf (M:N with attributes -> membership)
-- ---------------------------------------------------------------------
CREATE TABLE driver (
    driver_id       INTEGER PRIMARY KEY,
    licence_number  VARCHAR(30) NOT NULL,
    name            VARCHAR(100),
    carrier_name    VARCHAR(200),
    CONSTRAINT ak_driver_licence UNIQUE (licence_number)
);

CREATE TABLE membership (
    membership_id   INTEGER PRIMARY KEY,
    driver_id       INTEGER NOT NULL REFERENCES driver  (driver_id)       ON DELETE CASCADE,
    network_id      INTEGER NOT NULL REFERENCES network (organization_id) ON DELETE CASCADE,
    start_date      DATE NOT NULL,
    end_date        DATE,                                  -- NULL = still active
    CONSTRAINT ak_membership UNIQUE (driver_id, network_id, start_date),
    CONSTRAINT ck_membership_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

-- ---------------------------------------------------------------------
-- Indexes on FK columns not already covered by a UNIQUE constraint
-- ---------------------------------------------------------------------
CREATE INDEX ix_station_owner      ON station (owner_id);
CREATE INDEX ix_station_operator   ON station (operator_id);
CREATE INDEX ix_station_network    ON station (network_id);
CREATE INDEX ix_port_connector     ON port (connector_type_id);
CREATE INDEX ix_adapter_from       ON adapter (from_connector_type_id);
CREATE INDEX ix_adapter_to         ON adapter (to_connector_type_id);
CREATE INDEX ix_accepts_connector  ON vehicle_accepts (connector_type_id);
CREATE INDEX ix_membership_network ON membership (network_id);

-- ---------------------------------------------------------------------
-- ISA "total": every organization must play at least one role.
-- Checked at COMMIT so the superclass row and its subclass row(s)
-- can be inserted in the same transaction.
```

## 14. cmn 도메인 필드 사전 — 모든 원본 컬럼의 주석 기준
제공 SQL의 **13개 테이블, 65개 컬럼**을 전부 포함한다. 아래 설명을 각 도메인 필드 바로 앞 한국어 주석의 기준으로 사용한다. PK/FK/AK 표기는 실제 코드·ORM에서 별도로 보존하며, 주석은 비전공자가 현실의 대상과 혼동하지 않게 설명한다.

### 14.1. `organization` → `cmn/organization.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `organization_id` | 이 기관이나 회사 하나를 서비스 안에서 구별하는 번호입니다. 사업자등록번호가 아닙니다. |
| `name` | 기관이나 회사의 이름입니다. 예: 충전 네트워크 회사명. 서로 다른 조직을 이름만으로 자동 합치지 않습니다. |
| `website` | 이 기관이 안내하는 웹사이트 주소입니다. None이면 등록된 주소가 없습니다. |

### 14.2. `site_owner` → `cmn/site_owner.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `organization_id` | 충전소 부지나 시설을 소유한 기관을 가리키는 번호입니다. organization의 같은 번호를 사용합니다. |
| `business_type` | 부지 소유자의 업종이나 시설 종류입니다. 예: 쇼핑센터·숙박시설. 충전 커넥터 종류가 아닙니다. |

### 14.3. `operator` → `cmn/operator.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `organization_id` | 충전 설비를 운영·관리하는 기관을 가리킵니다. 소유자 또는 네트워크와 다른 회사일 수 있습니다. |
| `support_phone` | 충전 설비 이용 문제를 문의할 운영사의 전화번호입니다. 운전자의 전화번호가 아닙니다. |

### 14.4. `network` → `cmn/network.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `organization_id` | 멤버십·결제 서비스를 제공하는 충전 네트워크 기관의 번호입니다. network_id FK가 이 번호를 참조합니다. |
| `payment_method` | 네트워크가 안내한 결제 방식 설명입니다. 이 문장만으로 게스트 결제 가능 여부를 확정하지 않습니다. |

### 14.5. `station` → `cmn/station.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `station_id` | 충전소 한 곳을 프로그램 안에서 구별하는 번호입니다. 외부 제공자의 충전소 번호와 구분합니다. |
| `latitude` | 충전소 위치의 위도입니다. 도 단위이며 북위는 양수, 허용 범위는 -90에서 90입니다. |
| `longitude` | 충전소 위치의 경도입니다. 도 단위이며 서경은 음수, 허용 범위는 -180에서 180입니다. |
| `name` | 운전자에게 보여 줄 충전소 이름입니다. 이름이 없을 수도 있습니다. |
| `street` | 충전소가 있는 도로명·번지 등 거리 주소입니다. 경도·위도와는 별개입니다. |
| `city` | 충전소가 속한 도시 이름입니다. 운전자의 거주 도시가 아닙니다. |
| `province` | 충전소가 속한 주 이름 또는 코드입니다. MVP는 BC 데이터를 대상으로 합니다. |
| `status` | 공개 데이터에 기록된 시설 상태입니다. 현재 포트의 고장·점유·대기 줄을 뜻하지 않습니다. |
| `access_restriction` | 누가 이곳을 이용할 수 있는지 설명한 제한입니다. 예: 고객 전용·플릿 전용. 도로 통행 허가를 대신하지 않습니다. |
| `accepts_guest_payment` | 멤버십 없이 결제를 받는지에 관한 DB 값입니다. 직접 입력·검수한 값은 그대로 사용하고 외부 수집 기본값인 경우 메타데이터에서 미확인으로 표시합니다. |
| `max_vehicle_class` | 시설이 받을 수 있다고 안내한 차량 등급 제한입니다. 미기재를 모든 차량 허용으로 해석하지 않습니다. |
| `has_truck_parking` | 트럭 주차 공간이 있다고 기록했는지 나타내는 DB 값입니다. 기본 false와 미확인은 다르며 충전 베이 진입을 보장하지 않습니다. |
| `owner_id` | 이 충전소 부지·시설의 소유자 역할을 가리킵니다. site_owner의 조직 번호입니다. |
| `operator_id` | 충전 설비를 실제 운영·관리하는 역할을 가리킵니다. operator의 조직 번호입니다. |
| `network_id` | 이 충전소에서 사용하는 충전 네트워크의 조직 번호입니다. None이면 연결된 네트워크가 기록되지 않았습니다. |

### 14.6. `connector_type` → `cmn/connector_type.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `connector_type_id` | 커넥터 규격 한 종류를 구별하는 번호입니다. 개별 충전기나 포트의 번호가 아닙니다. |
| `name` | 충전기 플러그·차량 충전구의 규격 이름입니다. 예: CCS1. 이름 별칭은 별도 검수합니다. |
| `max_power_kw` | 해당 규격에 대해 기록된 최대 출력 참고값입니다. 단위는 kW이며 모든 제품의 실제 속도를 보장하지 않습니다. |

### 14.7. `port` → `cmn/port.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `port_id` | 충전소 안의 포트 또는 공급자가 묶어 기록한 포트 항목을 구별하는 번호입니다. 실시간 가용 포트 수가 아닙니다. |
| `station_id` | 이 포트 항목이 설치된 충전소를 가리키는 번호입니다. |
| `number` | 같은 충전소 안에서 이 포트 항목을 구별하는 양의 번호입니다. 다른 충전소에서는 같은 번호를 쓸 수 있습니다. |
| `connector_type_id` | 이 포트가 제공하는 커넥터 규격을 가리킵니다. 차량이 받는 규격과 비교합니다. |
| `power_kw` | 이 포트 항목에 기록된 출력 상한입니다. 단위는 kW이며 실제 충전 속도는 차량·환경에 따라 달라집니다. |
| `current_type` | 포트가 공급하는 전기의 종류입니다. AC는 교류, DC는 직류이며 None이면 확인되지 않았습니다. |
| `quantity` | 공급자가 이 항목에 묶어 기록한 개수입니다. 기본값은 1이며 물리 포트/커넥터 중 무엇을 세었는지는 별도 근거로 확인합니다. |

### 14.8. `operating_period` → `cmn/operating_period.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `operating_period_id` | 요일별 운영 구간 한 개를 구별하는 번호입니다. 충전 예약 번호가 아닙니다. |
| `station_id` | 이 운영시간이 적용되는 충전소 번호입니다. |
| `day` | 충전소 현지 기준 요일입니다. Mon에서 Sun까지의 영문 세 글자를 사용합니다. |
| `open_time` | 그 요일에 이용을 시작할 수 있는 현지 시각입니다. 이 시각을 포함하며 24:00은 시작값으로 쓰지 않습니다. |
| `close_time` | 그 요일에 이용이 끝나는 현지 시각입니다. 이 시각은 포함하지 않으며 24:00은 그날 끝의 자정입니다. 야간은 날짜별 두 행으로 나눕니다. |

### 14.9. `adapter` → `cmn/adapter.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `adapter_id` | 어댑터 모델 하나를 구별하는 번호입니다. 특정 운전자가 소유한 실물 제품의 일련번호가 아닙니다. |
| `model` | 어댑터 제품의 모델명입니다. 제공 DDL에서 같은 모델명을 중복 저장하지 않습니다. |
| `manufacturer` | 어댑터를 만든 제조사 이름입니다. 차량 제조사와 항상 같지는 않습니다. |
| `max_power_kw` | 어댑터가 허용한다고 기록된 출력 상한입니다. 단위는 kW이며 미기재면 최대 출력을 확정할 수 없습니다. |
| `from_connector_type_id` | 어댑터의 충전기 쪽이 받아들이는 플러그 규격입니다. 반대 방향 사용 가능성을 뜻하지 않습니다. |
| `to_connector_type_id` | 어댑터의 차량 쪽이 연결되는 충전구 규격입니다. 방향만 맞아도 실제 호환이 검증된 것은 아닙니다. |

### 14.10. `vehicle` → `cmn/vehicle.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `vehicle_id` | DB의 차량 한 대를 구별하는 내부 번호입니다. 검색 시 선택한 차량을 가리키는 ID로 사용합니다. |
| `vin` | 제조사가 차량 한 대에 부여한 17자리 차대번호입니다. 차량 등록 폼에서 입력받아 vehicle 테이블에 저장합니다. |
| `licence_plate` | 차량 번호판에 적힌 번호입니다. 차량 등록·수정 폼에서 입력받아 DB에 저장합니다. |
| `make` | 차량을 만든 회사나 브랜드 이름입니다. |
| `model` | 차량 모델 이름입니다. 같은 이름이어도 연식·사양에 따라 충전 조건이 다를 수 있습니다. |
| `class` / `vehicle_class` | 차량 크기·종류의 등급입니다. Python 필드는 vehicle_class이며 원본 DB 컬럼 class에 매핑합니다. |
| `range_km` | 기록된 주행 가능 거리의 참고값입니다. 단위는 km이며 현재 배터리로 갈 수 있는 거리가 아닙니다. |
| `max_charge_kw` | 차량에 기록된 최대 충전 출력입니다. 단위는 kW이며 모든 충전 상황에서 이 속도가 나오는 것은 아닙니다. |

### 14.11. `vehicle_accepts` → `cmn/vehicle_accepts.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `vehicle_accepts_id` | 차량과 수용 가능한 커넥터 규격의 연결 기록 하나를 구별하는 번호입니다. |
| `vehicle_id` | 해당 커넥터를 받아들일 수 있다고 기록한 차량의 내부 번호입니다. |
| `connector_type_id` | 이 차량이 수용한다고 기록된 커넥터 규격 번호입니다. 원본 테이블에는 차량별 AC/DC 추가 정보가 없으므로 규격만으로 확정할 수 없는 연결은 확인 필요로 처리합니다. |

### 14.12. `driver` → `cmn/driver.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `driver_id` | DB의 운전자 한 명을 구별하는 내부 번호입니다. 로그인 계정이나 브라우저 추적 ID가 아닙니다. |
| `licence_number` | 실제 세계의 운전면허번호에 대응하는 필드입니다. 운전자 등록·수정 폼에서 입력받아 driver 테이블에 저장합니다. |
| `name` | 운전자의 이름에 대응하는 필드입니다. 운전자 등록·수정 폼에서 입력받아 저장합니다. |
| `carrier_name` | 운전자가 속한 운송사 이름입니다. 충전 네트워크 이름과 다르며 운전자 등록·수정 폼에서 입력받아 저장합니다. |

### 14.13. `membership` → `cmn/membership.py`

| SQL 컬럼 / Python 필드 | 필드 주석 기준 |
|---|---|
| `membership_id` | 운전자의 네트워크 가입 기록 한 개를 구별하는 번호입니다. 카드 번호나 결제 인증 정보가 아닙니다. |
| `driver_id` | 이 가입 기록의 운전자를 가리킵니다. 면허번호 자체를 저장하는 필드가 아닙니다. |
| `network_id` | 가입한 충전 네트워크의 조직 번호입니다. 충전소의 network_id와 비교합니다. |
| `start_date` | 멤버십이 시작되는 현지 날짜입니다. 이 날짜를 포함합니다. |
| `end_date` | 마지막 유효 날짜입니다. 이 날짜를 포함하고 None이면 종료일이 따로 기록되지 않은 상태입니다. |
