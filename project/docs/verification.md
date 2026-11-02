# PluggedIn 검증 기록

## 2026-10-27 사용자 요청 반영

- 웹사이트·접근성 레이블·지도 팝업·판정 이유·입력 오류를 영어로 변경했다. 사용자 입력 데이터와 개발자용 한국어 주석은 유지한다.
- 날짜 달력과 시간 선택란, 명시적인 Pacific time (BC)/UTC 선택을 추가했다. 현지 시각을 서버에서 aware instant로 변환하며 기존 arrival_at URL/API를 지원한다.
- 부분 입력·잘못된 날짜·시간·시간대 및 과거 DST의 존재하지 않거나 중복되는 시각을 오류로 안내한다. Search now는 입력된 과거 조건을 무시하고 JS 없이 요청 시각으로 검색한다.
- 목록과 상세는 읽기 쉬운 영어 날짜·시간을 표시하며 같은 instant를 유지한다.
- 최종 명령: `venv/Scripts/python.exe -m pytest -q --basetemp=.work/pytest-english-final --browser chromium`.
- 결과: **170 tests passed, 91 subtests passed, 34.77초**. upstream TestClient/httpx deprecation warning 1개, 실패·skip 없음.
- Chromium에서 영어 페이지·실제 date/time 입력·무JS 검색·상세 이동·Search now·모바일 6개 페이지와 기존 CRUD·지도 흐름을 검증했다. 실행 중인 서버를 재시작하고 실제 영어 화면도 확인했다.
- SQLite 실제 파일: `D:\CSC 501\PluggedIn\project\src\ca\uvic\ecs\csc501\dal\data\pluggedin.db`. 이번 변경에서는 DB 구조나 기존 저장값을 변경하지 않았다.

아래는 최초 MVP 구현 시점의 검증 기록이다.

검증 기준일: 2026-10-26. 승인된 v3.0.0 기획서와 구현 설계를 기준으로 Windows에서 실행했다.

## 실제 실행 결과

- Python 3.12.14로 프로젝트 venv 생성, requirements 설치, editable 패키지 설치 성공.
- FastAPI 0.162.0, Uvicorn 0.54.0, SQLAlchemy 2.0.55, Jinja2 3.1.6, python-multipart 0.0.32, tzdata 2026.5 사용. 전체 설치 목록은 requirements-lock.txt.
- init_db → seed_demo → validate_db 실행 성공. 기본 dal/data/pluggedin.db를 생성했고 schema/data valid를 확인했다.
- 실제 Uvicorn 서버를 127.0.0.1:8000에서 실행했다.
- 실제 HTTP API로 임시 운전자 정보를 저장한 뒤 Uvicorn 프로세스를 종료·재시작했다. 새 프로세스에서 면허·이름·운송사 값이 동일함을 확인하고 임시 행은 삭제했다. 최종 서버는 실행 상태로 남겼다.
- 최종 전체 명령: `venv/Scripts/python.exe -m pytest -q --basetemp=.work/pytest-final --browser chromium`.
- 결과: **118 tests passed, 91 subtests passed, 23.79초**. 실패·skip 없음.
- 단위·DB·use case·HTTP·구조 검사와 실제 Chromium 브라우저 2개 시나리오를 한 번에 실행했다.
- `python -m pip check`: No broken requirements found. `python -m compileall -q src`: 성공.
- upstream Starlette가 TestClient의 httpx 사용에 deprecation warning 1개를 출력한다. 테스트 실패는 아니며 요구된 HTTPX/TestClient 검증을 그대로 사용했다.

기본 Windows Python 실행 별칭이 작동하지 않아 Codex 제공 Python의 실제 경로로 venv를 생성했다. 제한된 실행 환경에서는 임시 폴더와 asyncio loopback 통신이 막혔으며, 허용된 실행 환경에서 실제 설치·HTTP·브라우저 검증을 완료했다. 제한된 환경에서 멈춘 시도는 통과 수에 포함하지 않는다.

Linux/macOS 명령은 README에 제공하지만 이 세션에서 해당 OS로 실행하지 않았다.

## V01–V40 대응

- **V01:** venv 설치·editable src 패키지·Uvicorn 실제 실행. 별도 Node/DB 서버 없음.
- **V02:** tests/architecture의 계층 import 검사. main이 DAL/UoW와 use case·HTTP를 조립하며 static은 pl/static만 노출.
- **V03:** 13 entity/ORM의 65필드 대응 검사. 원본 class→vehicle_class 매핑과 한국어 필드 주석 코드 검토.
- **V04:** test_schema_models_and_foreign_keys_match에서 독립 연결의 FK PRAGMA 확인.
- **V05:** DB 통합 검사로 좌표·면허·VIN·복합키 중복 거부; HTTP 검사로 409/400 폼 오류와 기존 값 보존 확인. 승인 설계에 따라 명세에 없는 충전소 쓰기 API는 추가하지 않았다.
- **V06:** DDL/ORM FK·CHECK·삭제 동작, 역할 참조 및 cascade 통합 검사.
- **V07:** role-less 조직 commit 거부·rollback과 전체 seed transaction 검사; 직접 DB 우회는 validate로 탐지.
- **V08:** DailyTime 및 ORM 24:00 왕복, open=24·잘못된 clock·역순 CHECK 거부.
- **V09:** Driver 세 필드 생성·수정·SSR 복원·브라우저 저장 검사.
- **V10:** Vehicle 모든 입력과 수용 커넥터의 저장·편집 복원, 소수 출력 100.5의 무JS 브라우저 왕복 검사.
- **V11:** 멤버십 종료일 미지정·날짜 역순 오류·선택 ID 복원·기간 수정 검사.
- **V12:** 새 Database/ApplicationService 인스턴스로 동일 디스크 DB 재조회; 실제 Chromium의 별도 context에서 등록값 확인. 실제 Uvicorn 프로세스 종료·재시작 후 HTTP 재조회도 성공.
- **V13:** Driver→Membership 및 Vehicle→VehicleAccepts cascade가 독립적인지 검사.
- **V14:** 잘못된 수용 규격·중복·저장 범위 초과 입력에서 차량 및 수용 규격 전체 원자성 검사.
- **V15:** java_script_enabled=False에서 Driver/Vehicle/Membership 생성·수정·삭제와 검색·상세·길찾기 수행.
- **V16:** HTTP 응답 HTML 원문에 충전소명·상태·이유·폼 값·map-data가 이미 포함됨을 검사.
- **V17:** POST 성공303, 오류400 HTML, 텍스트·커넥터·멤버십 선택 보존 검사.
- **V18:** OpenStreetMap 타일 요청을 차단한 실제 Chromium에서 SSR 목록과 링크 유지.
- **V19:** 도착 현지 시각 개점 포함·폐점 제외 단위 검사.
- **V20:** 일요일→월요일 야간 분할과 새벽·폐점 경계 검사. 요일/날짜 연산을 사용하며 전날 시간표를 임의 확장하지 않음.
- **V21:** 시간표 누락·부분·잘못된 시간대 및 손상된 metadata 형태를 보수적 UNKNOWN으로 처리하는 검사.
- **V22:** 시설 상태 UNKNOWN에서 열린 시간표 UNKNOWN, 닫힌 완전 시간표 FAIL 검사.
- **V23:** 목록이 확정한 arrival_at을 상세 링크·평가에 유지; 폐점 시나리오 재현 검사.
- **V24:** tzdata 2026.5에서 2026-11-01·2026-12-01 Vancouver UTC−07 검사.
- **V25:** 직접 CCS1/DC·J1772/AC·CHAdeMO/DC와 완전 포트 불일치 검사.
- **V26:** 전류 미상·검증 불가 NACS/TESLA는 UNKNOWN; 어댑터 lookup 없이 평가.
- **V27:** 원본 adapter 참조 모델만 보존. 보유 관계·선택·추천·변환·소유 API/폼/localStorage 없음; 코드 검토.
- **V28:** 멤버십 현지 날짜 시작·종료 경계 포함 검사.
- **V29:** 선택 driver와 같은 network의 실제 DB 가입만 사용, 변경 시 재판정 검사.
- **V30:** guest=true PASS, network 미상+guest=false UNKNOWN, 원본 bool 미확인 UNKNOWN 검사.
- **V31:** 독립 기대값으로 3^4=81개 항목 상태 조합 검사.
- **V32:** 실제 포트 OR·부분 목록의 미확인 후보·공통 FAIL 보존·대표 직접 포트의 일관성 검사.
- **V33:** public 정규화, fleet/customer/미해석 제한 UNKNOWN 및 운송사명으로 승인하지 않는 동작 검사.
- **V34:** 차량 등급 초과 FAIL, 트럭 주차 기록만 있을 때 물리 조건 UNKNOWN 검사.
- **V35:** min(150,100)=100 및 출력 미상 null과 직접 호환 독립성 검사.
- **V36:** 좌표 UNIQUE 유지, 입력 좌표 조작·자동 합치기 없음.
- **V37:** HTML 입력 escaping·tojson·지도 팝업 textContent 사용 검사/검토. 원문 script는 실행 HTML로 삽입되지 않음.
- **V38:** 없는 ID404·입력400·중복409·미준비503 envelope, 초대형 정수 입력의400 변환 검사.
- **V39:** 비파괴 초기화·동일 seed 재실행·수정된 demo/metadata 충돌 보존 검사.
- **V40:** §9의 A/B/C/D/E 정답, Jin 멤버십 추가/삭제, 차량 수용 규격 변경의 실제 DB 재판정 및 브라우저 흐름 검사.

## 독립 검토와 보완

별도 에이전트가 도메인·DAL과 전체 프로젝트를 검토했다. 첫 core 검토에서 발견한 SQLite int64 범위 초과와 비정상 metadata JSON 형태 오류를 재현하는 테스트를 먼저 작성한 뒤 수정했다. 극단 날짜의 현지 시간 변환 overflow도 UNKNOWN으로 처리한다.

최종 독립 검토 판정: 지정 MVP 범위 승인, 남은 Critical/Important 결함 없음. 상세는 docs/superpowers/plans/final-review.md에 기록했다.

브라우저 검증에서 발견한 390px 화면의 grid 최소 너비 문제와 지도 fallback DOM 문제를 수정했다. Leaflet 1.9.4를 로컬에 포함한 뒤 실제 마커 5개·확대 컨트롤·무JS·타일 실패 흐름을 다시 검사했다. 12개 페이지의 모바일 너비도 확인했다.

## 남는 제품 범위

합성 충전소 데이터이며 실시간 현황·실제 결제·도로 통행·트럭 물리 진입·도달 가능성을 보증하지 않는다. 로그인·배포·권한 격리는 이번 기획서 범위에 포함되지 않는다. 원본 스키마와 단일 로컬 SQLite 구조를 유지한다.
