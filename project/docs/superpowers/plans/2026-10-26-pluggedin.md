# PluggedIn Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** 지정 기획서의 저장·판정·SSR·API가 실제 동작하는 학교 프로젝트 MVP.
**Architecture:** 순수 cmn 도메인·use case, dal ORM/UoW, pl SSR/API를 main에서 조립한다. 인터페이스를 먼저 고정해 독립 영역을 병렬 구현하고 전체 통합 검사를 수행한다.
**Tech Stack:** Python 3.12 venv, FastAPI/Jinja2, SQLAlchemy 2.x, SQLite, pytest, Playwright, Leaflet.
**Spec:** docs/PluggedIn_Development_Plan_AI_Agent.md 및 승인된 docs/superpowers/specs/2026-10-26-pluggedin-design.md

## Global Constraints

- src/ca/uvic/ecs/csc501, cmn/dal/pl 책임 준수. cmn은 프레임워크·DB·파일 I/O 금지, pl은 dal 직접 사용 금지.
- 원본 13테이블·65컬럼·키·관계·제약 보존. 모든 도메인 필드 앞 쉬운 한국어 주석.
- 실제 DB CRUD와 SSR. 운전자/차량 독립 선택. 보유 어댑터·변환 기능 제외.
- 기획서의 §6 SSR·§8 API·§9 demo·V01–V40이 기준. 미실행 검증을 통과로 보고하지 않는다.
- 수정·seed 재실행·서버 재시작은 기존 사용자 데이터를 보존한다.

## Review Focus

- 잘못된 폼·다중 선택 입력에서 값·체크 상태를 보존하고 DB는 그대로 유지한다.
- 알 수 없는 시간대·부분 포트 목록에서도 시설 공통 FAIL을 보존한다.
- DB 미초기화에서 health는 503이며 오류가 HTML/API 경계에 맞는다.
- seed 재실행 시 사용자가 변경한 demo 행을 덮어쓰지 않는다.
- HTML 및 map-data의 사용자 입력은 실행되지 않고 검색 시각은 상세까지 보존된다.

## Shared interfaces

정확한 모듈·필드·메서드 계약은 `docs/superpowers/plans/implementation-contract.md`에 고정한다. 구현 변경은 소비자와 함께 조정한다.

## Task 1: 순수 도메인·판정

**Files:** cmn의 13 entity 파일, value_objects, contracts, services, tests/unit/test_domain.py.
**Produces:** implementation-contract.md의 entity, snapshot, enum, evaluate_station.
- [x] 테스트를 먼저 작성: DailyTime 경계, membership 날짜, 81 AND 조합, demo 판정, 부분 포트·시간대·트럭·전류·출력.
- [x] venv Python으로 unit 테스트를 실행해 누락 기능 실패를 확인한다.
- [x] 순수 dataclass·값 객체·판정 서비스·한국어 필드 주석을 구현한다.
- [x] unit 테스트 통과 및 전체 변경 검토.

## Task 2: DB·ORM·repository·UoW·demo

**Files:** dal 전체, tests/integration/test_database.py.
**Consumes:** Task 1 entity/snapshot 및 공통 repository 계약.
**Produces:** Settings, Database, SqlAlchemyUnitOfWork, init_database, seed_demo, validate_database.
- [x] 임시 dal DB에서 DDL/ORM 65컬럼·FK·CHECK·cascade·rollback·seed 보존 테스트 작성 후 기대 실패 확인.
- [x] 제공 DDL을 추출하고 13 ORM 모델·mapper·repository·UoW 구현.
- [x] 설정 경로 제한, 연결 PRAGMA, 조직 역할·aggregate 검증, 비파괴 초기화·seed·검사 구현.
- [x] DB 통합 테스트 통과 및 원본 스키마 대응 검토.

## Task 3: SSR·API·템플릿·지도

**Files:** pl 전체, tests/integration/test_http.py.
**Consumes:** ApplicationService의 공유 메서드와 오류 계약. dal import 금지.
**Produces:** router, register_error_handlers, SSR 완성 HTML·snake_case JSON.
- [x] 실제 ApplicationService를 주입하는 HTTP 테스트 작성 후 기능 누락 실패 확인.
- [x] 기획서 SSR·CRUD·API·입력 DTO·오류 처리 구현.
- [x] 한국어 반응형 화면·CSS·Leaflet 보조 지도 구현. 폼 성공303·실패400, escaping·시각 보존 보장.
- [x] HTTP 테스트와 JS 없는 HTML 검사 통과.

## Task 4: use case·조립·로컬 환경

**Files:** cmn/application/services.py, main.py, pyproject.toml, requirements*.txt, AGENTS.md, tests/integration/test_application.py.
**Consumes:** Task 1/2/3의 공유 계약.
- [x] 저장→검색에 반영·잘못된 ID·atomic update·시간 고정·오류 계약 테스트 작성 후 실패 확인.
- [x] venv 및 src 패키징 구성, 순수 use case 구현, main에서 DB/UoW 주입.
- [x] 설치 검증된 정확 버전 고정, 초기화·seed·검사·서버 실행.
- [x] 통합 테스트 통과.

## Task 5: 브라우저·구조·최종 검토·인계

**Files:** tests/architecture/test_layers.py, tests/e2e/test_browser.py, README.md, docs/verification.md.
- [x] 계층 의존성과 domain/ORM 필드 대응 검사.
- [x] Chromium에서 CRUD→검색→상세, JS 비활성·타일 차단·다른 context 저장 유지 테스트.
- [x] V01–V40을 실제 결과와 대응. 전체 pytest 실행.
- [x] 독립 코드 검토 후 결함 수정과 관련 회귀 검사.
- [x] Windows/Linux 실행·demo·한계 README 작성 및 실행 중인 앱 안내.

## Execution ledger

사용자가 전체 구현 및 추가 세부 승인 생략을 승인했다. 상위 .git은 쓰기 허용 범위 밖이므로 현재 project 안에서 작업하고 상위 파일·Git 설정을 변경하지 않는다. 현재 앱/테스트가 없는 빈 project이므로 기존 실행 baseline은 없다. 독립 파일 소유권으로 병렬 작업하며 통합 이후 최종 검토한다.

