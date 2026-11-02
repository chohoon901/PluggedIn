# PluggedIn MVP 구현 설계

작성일: 2026-10-26  
상태: 사용자 승인 완료 — 2026-10-26, 이후 세부 구현 위임  
기준: `docs/PluggedIn_Development_Plan_AI_Agent.md` v3.0.0

## 1. 목적과 성공 기준

BC 전기차 운전자가 DB에 등록된 운전자와 차량을 각각 선택하고 도착 시각을 입력하면, 충전소의 운영시간·접근 조건·직접 커넥터 호환·결제 조건을 서버가 판정한다. 결과와 이유를 HTML 목록·상세에서 확인하고 외부 길찾기로 이동한다.

단순 지도나 정적 목업이 아닌 로컬 실행 가능한 학교 프로젝트 MVP를 만든다. 운전자·차량·수용 커넥터·멤버십은 실제 SQLite에 저장하며 서버 재시작과 다른 브라우저에서도 유지된다. 원 기획서 V01–V40을 검증 근거로 사용하며, 실행하지 못한 검증은 통과로 기록하지 않는다.

## 2. 이미 확정된 요구사항

- Python venv, FastAPI, Uvicorn, Jinja2 SSR, SQLAlchemy 2.x 동기 ORM, 로컬 SQLite를 사용한다.
- `src/ca/uvic/ecs/csc501`의 `cmn/dal/pl` 구조를 따른다.
- §13 DDL의 13테이블·65컬럼·키·관계·제약·8개 인덱스를 유지한다.
- §14에 따라 모든 순수 도메인 필드에 쉬운 한국어 주석을 작성한다.
- §6 SSR 라우트와 폼, §8 snake_case JSON API 계약을 구현한다.
- 운전자와 차량을 독립 선택한다. 원본에 없는 소유 관계를 추가하지 않는다.
- 어댑터 테이블·도메인·ORM만 보존하고 보유·선택·추천·변환 기능은 만들지 않는다.
- JavaScript 없이 CRUD·검색·결과·상세·길찾기를 사용할 수 있게 한다.
- 로그인·사용자별 권한·실제 결제·실시간 점유·자동 실데이터 수집·배포는 이번 범위 밖이다.

## 3. 구현 접근

기획서가 기술 구성과 계층 책임을 확정했으므로, 하나의 FastAPI 애플리케이션에서 SSR와 JSON API가 동일한 use case를 호출하는 구성을 채택한다.

SPA와 별도 프런트 빌드는 서버에서 완성 HTML을 반환해야 한다는 요구와 맞지 않는다. 별도 DB 서버나 마이크로서비스는 로컬 학교 MVP의 실행 부담을 늘리고 지정된 SQLite 구성을 벗어난다. 지정된 단일 애플리케이션 구성이 요구를 충족하는 유일한 범위 내 접근이다.

## 4. 계층 및 조립

### cmn: 순수 도메인과 애플리케이션

테이블별 dataclass/entity 13개, Location·DailyTime 값 객체, repository/UoW Protocol, 읽기 모델, enum, 네 판정 서비스, CRUD·검색·상세 use case를 둔다. FastAPI·Pydantic·SQLAlchemy·sqlite3·파일 I/O를 import하지 않는다.

도메인은 실제 필드와 단위를 표현한다. 좌표와 출력은 Decimal로 유지하고, 생성 전 ID만 None을 허용한다. `Vehicle.vehicle_class`는 Python 이름이며 저장 컬럼은 원본 `class`를 유지한다. `DailyTime`은 0–86400초를 표현하고 86400은 폐점에서만 허용한다.

### dal: 저장·메타데이터·트랜잭션

config.properties, 경로 검증, engine/session, 13 ORM 모델, mapper, repository, UoW, DDL 초기화·demo seed·DB 검사 스크립트를 둔다. DB 파일과 station_metadata.json은 dal/data 안에 둔다.

연결마다 foreign_keys=ON과 busy_timeout을 적용한다. 요청마다 Session 하나를 생성·종료하며 repository가 commit하지 않는다. UoW가 flush 후 조직 역할 및 aggregate 규칙을 검사하고 commit 또는 rollback한다. ORM 객체를 Session 밖으로 전달하지 않는다.

SQLite 스키마는 제공 DDL로 명시적으로 초기화한다. 앱 시작 시 create_all로 대체하거나 기존 DB를 지우지 않는다. 업무 CRUD는 ORM을 사용하고 raw SQL은 DDL·PRAGMA·스키마 검사에만 사용한다.

### pl: HTTP와 완성 HTML

라우터·Pydantic DTO·오류 처리·템플릿·CSS·보조 JS를 둔다. pl은 dal·Session·SQL을 직접 사용하지 않는다. main.py가 구체적인 dal 구현을 use case와 HTTP 의존성에 연결한다. DB를 사용하는 route는 동기 def로 구현한다.

SSR와 API는 같은 CRUD 및 평가 use case를 호출한다. HTML form 성공은 303 redirect, 입력 오류는 입력값과 선택을 보존한 400 HTML을 반환한다. API는 기획서의 400/404/409/503 오류 envelope를 사용한다.

## 5. 저장과 입력

Driver는 면허번호·이름·운송사, Vehicle은 VIN·차량번호·제조사·모델·등급·거리·출력 및 수용 규격, Membership은 운전자·네트워크·시작/종료일을 전부 지원한다. nullable 필드는 빈 입력을 None으로 정규화한다. VIN 17자·문자열 길이·양수·날짜 순서·참조 ID를 검증한다.

Vehicle와 VehicleAccepts 집합 교체는 동일 트랜잭션에서 수행한다. 수용 규격을 최소 하나 선택해야 한다. 실패하면 차량과 연결 모두 이전 값으로 유지한다. Driver 삭제는 Membership, Vehicle 삭제는 VehicleAccepts에만 원본 cascade를 적용한다. 동일 네트워크 가입 기간의 중첩은 허용하고 원본 복합키 중복만 거부한다.

Organization은 최소 하나의 owner/operator/network 역할을 가져야 한다. SQLite에 없는 지연 ISA 검사를 UoW와 validate_db에 구현한다. 불완전 demo 시설은 메타데이터에 명시하되 FK·NOT NULL·CHECK·UNIQUE와 조직 역할 규칙을 면제하지 않는다.

## 6. 판정

검색은 driver_id·vehicle_id로 DB 정보를 다시 읽으며 클라이언트가 제출한 사양이나 멤버십으로 우회하지 않는다. 요청 시각은 한 번만 확정한다. offset/Z가 있는 arrival_at을 UTC instant로 유지하고 충전소 현지 시간대로 변환한다. 목록에서 상세까지 같은 arrival_at을 전달한다.

각 포트 후보에서 opening/access/connector/payment를 함께 평가한다. 네 항목 AND는 FAIL 우선, 다음 UNKNOWN, 모두 PASS이면 AVAILABLE이다. 포트 후보 OR는 AVAILABLE 우선, 다음 NEEDS_REVIEW, 모두 실패하면 UNAVAILABLE이다. 서로 다른 포트의 장점을 합치지 않는다.

- opening: 시설 상태와 현지 시간표를 함께 평가한다. 개점 포함·폐점 제외이며 야간은 날짜별 두 행을 사용한다. 시간표가 완전할 때만 없는 요일을 휴무로 확정한다.
- access: public·명시 이용 금지·미해석 제한을 구별한다. 차량 등급 순서는 CAR<VAN<MEDIUM_TRUCK<HEAVY_TRUCK이다. 중대형 트럭은 주차 기록만으로 물리 진입을 확정하지 않고 UNKNOWN을 유지한다.
- connector: 수용 규격 ID와 일치하고 검증된 J1772/AC·CCS1/DC·CHAdeMO/DC 조합만 직접 호환 PASS로 확정한다. NACS/TESLA·전류 미상은 UNKNOWN이다. adapter를 조회하지 않는다.
- payment: 선택 운전자의 같은 네트워크 멤버십을 현지 날짜로 검사하며 시작일·종료일 모두 포함한다. 확인된 guest=true도 PASS다. 네트워크 미상·원본 bool 미확인은 UNKNOWN 정책을 적용한다.

포트 목록이 불완전하면 미확인 후보를 남기되, 시설 공통 폐쇄·접근 금지 같은 FAIL은 유지한다. 알려진 출력 높은 순, port_id 오름차순으로 후보를 결정한다. 출력 상한은 포트와 차량 값이 모두 알려졌을 때만 min이며 실제 속도로 표현하지 않는다.

모든 결과는 상태, 이유 코드, 쉬운 설명, 사용한 근거를 포함한다. 세부 enum과 필수 코드 목록은 원 기획서 §7.6을 그대로 따른다.

## 7. 화면과 지도

한국어 안내를 중심으로 공통 내비게이션에서 충전소 찾기·운전자·차량·멤버십을 이동한다. 읽기 쉬운 반응형 화면에서 폼 레이블, 오류 메시지, 상태 텍스트와 이유를 제공한다. 색만으로 의미를 전달하지 않는다.

첫 화면은 운전자/차량 독립 선택과 도착 시각 입력을 제공한다. 목록은 조건과 상태 개수·충전소별 판정·이유를 SSR로 표시한다. 상세는 네 판정과 근거, 포트·운영시간·기관·출처·갱신일을 표시한다. 지도는 동일 결과에 대한 보조 화면이다.

서버가 map-data JSON을 tojson으로 삽입하고 Leaflet이 이를 읽어 마커를 표시한다. JS나 타일 요청이 실패해도 SSR 목록과 링크가 유지된다. Leaflet 고정 버전·타일 attribution을 기록한다. 길찾기는 Google Maps 목적지 좌표 링크를 기본 구현 선택으로 사용한다.

## 8. 구현자가 정한 세부 해석

다음은 새로운 제품 요구가 아닌 명세의 빈 부분에 대한 제안이며 검토 시 변경할 수 있다.

1. PARTIAL/UNKNOWN 시간표는 알려진 열린 구간이 있어도 보수적으로 UNKNOWN으로 판정한다. 원 기획서 §7.2와 V21을 우선한다.
2. PLANNED 시설 상태와 규격·전류 조합의 검증되지 않은 경우는 UNKNOWN으로 처리한다. 확정된 폐쇄나 직접 규격 불일치가 있으면 해당 FAIL을 보존한다.
3. V05 좌표 중복은 DB 통합 검사로 증명한다. 명세에 없는 충전소 CRUD API를 추가하지 않고 409 HTTP 검사는 제공된 CRUD의 면허·VIN·멤버십 복합키로 증명한다.
4. 화면 색상·간격·카드 배치, 모듈 내부 이름, 테스트 세분화는 기획서 계약을 유지하는 범위에서 구현자가 정한다.
5. 정확한 라이브러리 버전은 설치·호환 검증한 값으로 고정한다. 시간대는 설치된 최신 tzdata의 실제 Vancouver 2026년 11월/12월 결과를 검사한다.

## 9. demo 및 검증

원 기획서 §9의 두 운전자·한 차량·두 네트워크·다섯 충전소를 그대로 seed한다. 2026-10-26T19:00:00Z의 Mina+Vehicle1에서 A/B/E AVAILABLE, C UNAVAILABLE, D NEEDS_REVIEW를 검증한다. 야간 B 폐쇄, Jin의 멤버십 변경, 차량 수용 규격 변경이 DB 저장 후 결과에 반영되는지 검사한다.

단위 검사는 81개 AND 조합, 포트 OR·불완전 목록, 시간 경계·야간·현지 날짜, 접근·직접 호환·결제를 다룬다. DB 통합 검사는 DDL/ORM 대응, FK·CHECK·UNIQUE·cascade, 조직 역할 검사, 원자적 수정·rollback, seed 재실행과 기존 데이터 보존을 다룬다.

HTTP 검사는 CRUD 상태 코드·오류 envelope·SSR 값 복원·escaping·동일 시각 전달을 다룬다. 구조 검사는 계층 의존성과 13도메인/65컬럼 대응을 다룬다. 브라우저 검사는 일반 및 JS 비활성 모드의 전체 시연, 다른 브라우저의 DB 값, 타일 차단 상태의 SSR 사용을 확인한다.

검증 DB는 임시 dal 디렉터리에 격리한다. 실제 로컬 venv 실행 결과와 V01–V40 대응·미실행 항목을 문서에 기록한다.

## 10. 전달물과 환경

소스·고정 의존성·pyproject·schema.sql·seed/validate 스크립트·테스트·README·프로젝트 지침을 제공한다. venv는 로컬에 생성하지만 버전 관리에 포함하지 않는다. README에 Windows/Linux 설치·초기화·실행·검증·demo·한계를 설명한다.

현재 project 폴더는 비어 있다. 기본 python 명령은 Windows 실행 별칭 문제로 실행되지 않지만 Codex 제공 Python 3.12.14와 pip 실행을 확인했다. 구현에서는 이 Python으로 프로젝트 venv를 생성한다. 의존성 설치와 브라우저 실행 가능 여부는 구현 단계에서 실제 확인한다.

상위 기존 README에는 과거 어댑터·경로 기능이 있으나 새 프로젝트의 범위는 이번 v3.0.0 기획서로 정한다. 상위 프로젝트 파일은 수정하지 않는다.
