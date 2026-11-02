# PluggedIn

운전자·차량·도착 시각을 선택하면 BC 충전소의 **운영시간, 이용·차량 제한, 직접 커넥터, 결제 조건**을 비교하는 학교 프로젝트 MVP입니다. 운전자·차량·수용 커넥터·멤버십을 SQLite에 저장하고 서버에서 결과와 이유를 계산해 HTML로 제공합니다.

웹사이트 화면·판정 설명·오류 메시지는 영어입니다. 도착 시각은 달력과 시간 선택란으로 입력하며 기본 시간대는 Pacific time (British Columbia)입니다. UTC를 선택할 수도 있습니다. 서버가 현지 입력을 정확한 시각으로 변환하므로 소비자가 ISO 문자열이나 UTC offset을 직접 입력할 필요가 없습니다. Search now는 JavaScript 없이 현재 시각으로 검색합니다. 기존 aware arrival_at API와 URL은 계속 지원합니다.

## 실행 환경

- Python 3.12 이상. 이 환경에서는 Python 3.12.14로 설치·검증했습니다.
- FastAPI + Jinja2 SSR, SQLAlchemy 2.0 ORM, 로컬 SQLite.
- 별도 Node 빌드, DB 서버, API 키가 필요하지 않습니다.
- 런타임 직접 의존성은 requirements.txt, 개발 의존성은 requirements-dev.txt에 설치 검증한 버전으로 고정했습니다. 전체 설치 버전은 requirements-lock.txt에 있습니다.

## Windows PowerShell

이 README가 있는 `project` 폴더에서 실행합니다.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pip install -e .
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.init_db
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.seed_demo
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.validate_db
.\venv\Scripts\python.exe -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
```

가상환경과 초기 데이터가 이미 준비됐다면 마지막 실행 명령만 사용합니다. Windows의 `python` 명령이 Microsoft Store 별칭으로 실행되지 않으면 실제 설치된 Python 3.12 이상의 실행 경로로 첫 명령을 실행합니다. 이 프로젝트의 기존 `venv\Scripts\python.exe`는 바로 사용할 수 있습니다.

## Linux/macOS

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements-dev.txt
venv/bin/python -m pip install -e .
venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.init_db
venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.seed_demo
venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.validate_db
venv/bin/python -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
```

페이지는 [http://127.0.0.1:8000](http://127.0.0.1:8000), API 문서는 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), 준비 상태는 [health](http://127.0.0.1:8000/api/v1/health)에서 확인합니다. DB 미초기화·스키마 불일치는 503으로 안내합니다.

## 시연

충전소와 운전자·차량은 **합성 demo 자료**입니다. 실제 시설 현황을 나타내지 않습니다.

1. 첫 화면에서 Mina와 Demo Van을 각각 선택합니다. 두 목록은 독립적이며 차량 소유 관계를 뜻하지 않습니다.
2. 도착 시각을 `2026-10-26T19:00:00Z`로 검색합니다. A·B·E는 이용 가능, C는 이용 어려움, D는 확인 필요입니다. [동일 조건으로 열기](http://127.0.0.1:8000/stations?driver_id=1&vehicle_id=1&arrival_at=2026-10-26T19%3A00%3A00Z).
3. `2026-10-27T05:00:00Z`로 검색하면 B는 영업시간 밖입니다.
4. Jin으로 바꾸면 A의 결제 조건은 미충족, E는 게스트 결제로 통과합니다. Jin에게 Demo Charging Company 멤버십을 추가하면 A가 이용 가능으로 바뀌며 삭제하면 원래 판정으로 돌아갑니다.
5. 차량의 수용 커넥터를 CHAdeMO만으로 수정하면 C는 직접 연결 통과, A는 직접 연결 미충족입니다.

운전자·차량·멤버십 메뉴에서 등록·조회·수정·삭제합니다. 선택 필드도 입력하면 모두 DB에 저장됩니다. JS를 꺼도 같은 흐름을 수행할 수 있습니다. 지도 타일이 실패해도 목록·판정·상세·길찾기 링크는 사용할 수 있습니다.

## 저장과 구조

소스 패키지: `src/ca/uvic/ecs/csc501`.

- `cmn`: 13 순수 도메인 모델, 값 객체, repository/UoW 계약, 판정 서비스, CRUD·검색 use case. 도메인 필드마다 한국어 설명을 둡니다.
- `dal`: 13 ORM 모델, mapper, repository, UoW, 설정·DB·메타데이터·스크립트. `Vehicle.vehicle_class`는 원본 DB 컬럼 `class`에 매핑합니다.
- `pl`: HTTP DTO, SSR/API 라우트, 템플릿·CSS·보조 JS·Leaflet 자산.
- `main.py`: 의존성 조립과 pl/static 마운트.

DB는 `src/ca/uvic/ecs/csc501/dal/data/pluggedin.db`에 저장됩니다. 면허번호·이름·운송사, VIN·차량번호·사양·수용 규격, 네트워크 가입 기간을 실제 SQL 행으로 저장합니다. 브라우저 localStorage에 프로필을 저장하지 않습니다.

`dal/config.properties`의 DB 경로는 dal 기준입니다. dal 경계를 벗어나는 경로를 거부합니다. 시간대·시간표/포트 완전성·출처·미확인 필드는 `dal/data/station_metadata.json`에서 읽으며 개인 정보는 이 파일에 저장하지 않습니다. DB와 프로젝트 루트는 웹 정적 경로로 노출하지 않습니다.

제공 DDL의 **13테이블·65컬럼·8인덱스**와 키·관계·제약을 유지합니다. 연결마다 foreign_keys=ON과 busy_timeout을 적용합니다. repository는 commit하지 않고 요청별 UoW가 flush·검사·commit/rollback을 처리합니다. 차량과 수용 규격 집합은 함께 저장하거나 함께 되돌립니다.

SQLite에는 원본 PostgreSQL 지연 ISA 트리거가 없어 조직의 최소 한 역할 및 aggregate 무결성을 UoW에서 검사합니다. 직접 DB 도구의 쓰기는 이 검사를 우회할 수 있으므로 validate_db로 재검사합니다. 명시적으로 INCOMPLETE인 demo D의 시간표 누락만 허용합니다. VARCHAR 길이·NUMERIC 정밀도는 도메인/입력에서도 검증합니다.

init_db는 기존 DB를 교체하지 않고 스키마를 확인합니다. seed_demo는 동일 행을 중복 생성하지 않으며 사용자가 바꾼 demo 값과 충돌하면 중단하고 보존합니다. **평상시 재실행에는 seed_demo를 반복할 필요가 없습니다.** DB 관계는 한 트랜잭션, 메타데이터 파일은 임시 파일 후 원자적 교체로 저장합니다. DB commit 뒤 파일 쓰기가 실패하면 원인을 해결하고 seed를 재실행해 복구할 수 있습니다.

## 판정과 한계

항목은 PASS/FAIL/UNKNOWN, 종합은 AVAILABLE/UNAVAILABLE/NEEDS_REVIEW입니다. 네 항목 AND는 실패, 미상 순으로 우선합니다. 여러 포트는 같은 포트의 조건을 함께 평가한 후 가능한 후보를 선택합니다. 불완전 정보는 확정 통과로 처리하지 않습니다.

도착 시각에 Z 또는 UTC offset을 명시합니다. 목록→상세에서 같은 instant를 유지하고 시설 IANA 시간대로 변환합니다. 운영시간은 개점 포함·폐점 제외이며 `24:00:00`은 폐점에만 사용합니다. Vancouver의 2026년 11월/12월 UTC−07 적용을 tzdata 2026.5로 검증합니다.

- 직접 규격·전류 조합만 판정합니다. adapter 테이블·모델은 원본 보존용이며 보유·선택·추천·변환 API는 없습니다.
- 중·대형 트럭의 물리적 진입 여유는 주차 기록만으로 확정하지 않습니다.
- 출력은 포트와 차량 상한의 최소값이며 하나라도 미상이면 출력 미상입니다.
- 실시간 고장·점유·대기, 실제 잔액·결제 인증, 로밍, 도로 통행·높이·축중·회전 반경, SoC 도달성은 평가하지 않습니다.
- 로그인·멀티유저 권한·사용자별 소유 관계·실제 결제·배포는 범위 밖입니다.
- 서로 다른 시설의 같은 좌표는 원본 UNIQUE 제약을 유지합니다. 좌표를 조작하거나 자동 병합하지 않습니다.

## 검증

Windows:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit tests/integration tests/architecture
.\venv\Scripts\python.exe -m playwright install chromium
.\venv\Scripts\python.exe -m pytest tests/e2e --browser chromium
```

Linux/macOS:

```bash
venv/bin/python -m pytest tests/unit tests/integration tests/architecture
venv/bin/python -m playwright install chromium
venv/bin/python -m pytest tests/e2e --browser chromium
```

전체 검사는 `python -m pytest`로 실행합니다. 테스트 DB는 임시 dal 디렉터리에 격리합니다. 임시 폴더 접근이 제한된 환경에서는 `--basetemp=.work/pytest-run`을 덧붙일 수 있습니다. Windows에서 로컬 loopback 통신·브라우저 프로세스가 제한된 도구 환경은 해당 실행 허용이 필요합니다.

실제 검증 결과와 V01–V40 대응은 `docs/verification.md`에 기록합니다. 원 기획서는 `docs/PluggedIn_Development_Plan_AI_Agent.md`, 승인 설계와 구현 계획·검토 기록은 `docs/superpowers/`에 있습니다.

## 지도와 참고

Leaflet **1.9.4** JS/CSS 및 라이선스는 `pl/static/vendor`에 포함합니다. 타일은 [OpenStreetMap](https://www.openstreetmap.org/copyright)이며 지도에 attribution을 표시합니다. 외부 길찾기는 목적지 좌표만 담은 Google Maps 링크를 사용합니다. 외부 폰트를 불러오지 못하면 시스템 글꼴을 사용합니다.

구현 참고: [FastAPI 템플릿](https://fastapi.tiangolo.com/advanced/templates/), [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html), [IANA 시간대](https://www.iana.org/time-zones).
