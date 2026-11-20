# PluggedIn 팀원용 로컬 실행 가이드

이 가이드는 Windows와 macOS에서 각자의 Virtuoso로 PluggedIn을 실행하는 방법을 안내합니다. `715bb9f` (`Migrate PluggedIn storage to Virtuoso RDF`)가 포함된 팀 브랜치를 사용합니다. 저장소에 포함된 `sample20` SQLite 파일과 충전소 메타데이터로 시연용 그래프를 만듭니다.

## 1. 프로젝트와 Virtuoso 준비

- Python 3.12 이상, Git, 로컬 OpenLink Virtuoso 서버가 필요합니다. 그래프 관리는 Conductor 또는 Virtuoso SQL 클라이언트에서 할 수 있습니다.
- 팀 브랜치를 이미 추적 중이라면 저장소 루트에서 `git pull --ff-only`를 실행합니다. 이후 터미널 명령은 같은 위치에서 `cd project`한 뒤 실행합니다.
- 설치한 Virtuoso 서버를 시작합니다. 기본 HTTP 주소는 `http://127.0.0.1:8890`입니다. Conductor를 쓴다면 브라우저에서 `http://127.0.0.1:8890/conductor`를 엽니다. 포트가 다르면 설치 설정의 `[HTTPServer]`에 있는 포트를 사용합니다.

## 2. 앱 전용 그래프 준비

**이미 이 가이드의 이관 명령으로 앱 그래프를 만들었다면** 기존 그래프와 계정을 사용합니다. 3단계에서 연결을 설정한 뒤 4단계의 **기존 앱 그래프** 명령을 실행합니다.

**예전에 RDF 파일만 업로드했거나 이번이 첫 실행이라면** 앱용 그래프를 준비합니다. 기존 RDF를 올린 기본 그래프는 `https://github.com/chohoon901/PluggedIn/graph/`입니다. 앱 그래프의 기본 이름은 다음과 같습니다.

```text
https://github.com/chohoon901/PluggedIn/graph/app/
```

이미 앱 그래프 이름에 수동으로 RDF를 올려둔 경우, 빈 그래프 이름을 새로 정합니다. 설정 파일의 `app_graph_iri`와 아래 SQL의 앱 그래프 이름을 둘 다 새 이름으로 바꾸면 기존 RDF를 보관하면서 이관할 수 있습니다. [config.properties](../src/ca/uvic/ecs/csc501/dal/config.properties)

앱용 로컬 Virtuoso에서 관리자 계정으로 **Conductor → Interactive SQL**을 열거나 SQL 클라이언트에서 관리자 세션을 엽니다. 아래 예시의 `YOUR_LOCAL_PASSWORD`를 이 PC에서 사용할 앱 계정의 암호로 바꿔 실행합니다. `pluggedin_app` 계정이 이미 있으면 첫 줄은 건너뜁니다.

아래 `nobody` 설정은 이 인스턴스의 `PrivateGraphs` 그룹 전체에 적용됩니다. 다른 프로젝트가 그 그룹이나 기존 계정 권한을 사용 중이라면, 문서 하단의 **다른 로컬 Virtuoso 인스턴스가 필요한 경우**를 따라 앱 전용 인스턴스에서 실행합니다. [OpenLink 그래프 권한 안내](https://docs.openlinksw.com/virtuoso/rdfgraphsecurityintconfsec/)

```sql
DB.DBA.USER_CREATE ('pluggedin_app', 'YOUR_LOCAL_PASSWORD', VECTOR ('SQL_ENABLE', 1, 'DAV_ENABLE', 0));
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 0, 1);
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('pluggedin_app', 0, 0);
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('pluggedin_app', 0, 1);
DB.DBA.RDF_GRAPH_GROUP_INS (
  'http://www.openlinksw.com/schemas/virtrdf#PrivateGraphs',
  'https://github.com/chohoon901/PluggedIn/graph/app/'
);
DB.DBA.RDF_GRAPH_USER_PERMS_SET ('https://github.com/chohoon901/PluggedIn/graph/app/', 'pluggedin_app', 3);
GRANT SPARQL_UPDATE TO "pluggedin_app";
```

## 3. Python 환경과 연결 설정

운영체제에 맞는 명령을 실행합니다. Virtuoso HTTP 포트가 다르면 `PLUGGEDIN_VIRTUOSO_ORIGIN`의 `8890`을 바꿉니다. 예를 들어 Virtuoso를 `8893`으로 열었다면 `http://127.0.0.1:8893`을 사용합니다. 이후 단계도 암호를 입력한 **같은 터미널**에서 실행합니다.

### Windows PowerShell

```powershell
if (-not (Test-Path .\venv\Scripts\python.exe)) { py -3 -m venv venv }
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -m pip install -e .

$env:PLUGGEDIN_VIRTUOSO_ORIGIN = 'http://127.0.0.1:8890'
$credential = Get-Credential -UserName 'pluggedin_app' -Message 'Local Virtuoso app account'
$env:PLUGGEDIN_VIRTUOSO_USER = $credential.UserName
$env:PLUGGEDIN_VIRTUOSO_PASSWORD = $credential.GetNetworkCredential().Password
Remove-Variable credential
```

`py`가 없으면 Python 버전을 확인한 후 `python -m venv venv`로 가상환경을 만듭니다.

### macOS Terminal

```bash
if [ ! -x ./venv/bin/python ]; then python3 -m venv venv; fi
./venv/bin/python --version
./venv/bin/python -m pip install -e .

export PLUGGEDIN_VIRTUOSO_ORIGIN='http://127.0.0.1:8890'
export PLUGGEDIN_VIRTUOSO_USER='pluggedin_app'
printf 'Local Virtuoso app password: '
IFS= read -rs PLUGGEDIN_VIRTUOSO_PASSWORD
printf '\n'
export PLUGGEDIN_VIRTUOSO_PASSWORD
```

## 4. 샘플 데이터 적용

### 첫 실행 또는 기존 RDF만 업로드한 경우

Git에 포함된 SQLite와 메타데이터를 준비한 빈 앱 그래프에 한 번 이관합니다. 초기 샘플의 완료 메시지는 `Verified 193 SQLite records in the private Virtuoso graph.`입니다. 충전소 출력과 어댑터 근거도 이 단계에서 추가됩니다.

**Windows**

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso
```

**macOS**

```bash
./venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso
```

### 기존 앱 그래프에 새 커밋을 적용하는 경우

앱을 종료하고 최신 코드로 업데이트한 뒤 아래 명령을 실행합니다. `Sample20 equipment evidence is ready.`가 나오면 기존 그래프에 출력과 어댑터 근거가 적용된 것입니다. 같은 명령을 다시 실행해도 동일한 트리플은 한 번만 저장됩니다. [적용되는 SPARQL 업데이트](../src/ca/uvic/ecs/csc501/dal/semantic/queries/sample20_equipment_evidence.ru)

**Windows**

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --sample-equipment
```

**macOS**

```bash
./venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --sample-equipment
```

## 5. 앱 실행

`--check`에서 `Virtuoso application graph is ready.`를 확인한 뒤 서버를 시작합니다.

**Windows**

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --check
if ($LASTEXITCODE -eq 0) {
    .\venv\Scripts\python.exe -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
}
```

**macOS**

```bash
./venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --check &&
  ./venv/bin/python -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
```

브라우저에서 앱을 엽니다. 앱을 종료할 때는 실행 중인 터미널에서 **Ctrl+C**를 누릅니다. 다음 실행에는 Virtuoso를 켜고 5단계로 돌아옵니다. 새 터미널이라면 3단계의 연결 환경 변수를 다시 설정합니다. [PluggedIn 열기](http://127.0.0.1:8000/)

## 6. 시연 순서와 예상 결과

1. **Find charging**에서 `Sample member (synthetic)`와 `J1772 test car (synthetic)`를 고릅니다. 날짜는 `2026-11-02`, 시간은 `12:00`, 시간대는 `Pacific time (British Columbia)`로 설정하고 **Find stations**를 누릅니다. 초기 샘플의 기본 검색 범위에서 **20곳**이 나오고, **Available 1, Needs review 19, Unavailable 0**이 표시됩니다. **SWTCH Energy (5965 Student Union Blvd)** 상세에서 **Direct connection**이 **Pass**인지 확인합니다.
2. **Fast Charging (CQ2)**에서 `0` 또는 `50` kW를 검색하면 **Kaslo**와 **Norgate Park**, `250` kW에서는 **Kaslo**, `251` kW에서는 빈 결과가 나옵니다. Norgate Park는 50 kW이며 커넥터별로 두 줄에 표시됩니다. [Norgate Park 설치 자료](https://www.prismengineering.com/projects/district-of-north-vancouver-ev-design-and-implementation/)
3. **Adapter Finder (CQ4)**에서 샘플 차량을 골라 **Search stations**를 누릅니다. 각 샘플 차량마다 후보가 한 개 이상 있습니다. 표에서 충전소, 포트와 차량 커넥터의 방향, 어댑터 제품 링크를 보여줍니다. 후보는 커넥터 기준이므로 실제 이용 전에는 차량과 충전 네트워크의 조건을 확인합니다.
4. **Drivers**, **Vehicles**, **Memberships**에서 시연용 프로필을 확인합니다. 저장을 보여주려면 **Drivers → Add driver**에서 새 가짜 면허번호로 테스트 운전자를 저장하고, 브라우저를 새로 열어 조회한 다음 수정·삭제합니다.
5. **CQ1과 CQ3의 결과표**를 보여주려면 쿼리 파일의 두 `PREFIX`와 해당 `SELECT` 하나를 복사하고 `GRAPH`에 앱 그래프 이름을 넣습니다. **Interactive SQL**에서는 첫 줄에 `SPARQL`, 마지막에 `;`를 붙여 실행합니다. 초기 샘플에서 **CQ1**은 BC Hydro DoubleTree 충전소 1곳과 좌표를, **CQ3**은 Vancouver의 직접 연결 일치 8건을 반환합니다. [sparql_queries.rq](../src/ca/uvic/ecs/csc501/dal/semantic/queries/sparql_queries.rq)

## 문제가 생기면

- **접속 실패 또는 인증 오류**. Virtuoso 실행 상태, `PLUGGEDIN_VIRTUOSO_ORIGIN`에 지정한 HTTP 포트, 전용 계정 정보를 확인합니다.
- **그래프가 이미 데이터를 포함한다는 오류**. 먼저 `--check`를 실행합니다. 준비된 그래프라면 4단계의 기존 그래프 명령을 사용합니다. 수동 업로드한 그래프라면 2단계에서 빈 앱 그래프 이름을 지정합니다.
- **비공개 그래프 오류 또는 `RDF99`**. 2단계의 그래프 이름과 접근 권한을 확인합니다. 기존 Virtuoso의 비공개 그래프를 다른 작업에서도 사용 중이면 앱용 로컬 인스턴스로 전환합니다.
- **50 kW에서 Kaslo만 표시**. 최신 앱 코드를 받았는지 확인하고 4단계의 기존 그래프 명령을 실행한 뒤 앱을 다시 시작합니다.
- **8000번이 사용 중**. 앱 시작 명령의 `--port 8000`을 `--port 8001`로 바꿉니다. [8001번 앱 열기](http://127.0.0.1:8001/)

### 다른 로컬 Virtuoso 인스턴스가 필요한 경우

설치한 Virtuoso의 예제 `virtuoso.ini`를 새 빈 작업 폴더에 복사합니다. DB, 트랜잭션 로그, 잠금 파일, 임시 DB 경로가 새 폴더 안을 가리키는지 확인합니다. 비어 있는 포트로 `[Parameters]`의 `ServerPort`를 `127.0.0.1:1113`, `[HTTPServer]`의 `ServerPort`를 `127.0.0.1:8893`처럼 따로 지정합니다. 새 폴더에서 설치된 Virtuoso 서버 실행 파일에 `-f -c virtuoso.ini`를 붙여 시작합니다. Conductor는 8893번, SQL 클라이언트는 1113번을 사용해 2단계를 진행하고, 3단계에서 `http://127.0.0.1:8893`을 지정합니다. [OpenLink 서버 설정 안내](https://docs.openlinksw.com/virtuoso/ch-server/)

### RDF 변경분만 수동으로 적용하는 경우

같은 `sample20` 충전소와 포트가 들어 있는 그래프에 업데이트 파일을 적용할 수 있습니다. 파일의 모든 `GRAPH`를 대상 그래프에 맞추고 `#`로 시작하는 주석 줄을 제거합니다. 맨 앞에 `SPARQL`, 맨 끝에 `;`를 붙여 **Interactive SQL**에서 실행합니다. 앱 화면에서도 새 결과를 보려면 최신 CQ2 쿼리가 있는 코드를 사용합니다. [sample20_equipment_evidence.ru](../src/ca/uvic/ecs/csc501/dal/semantic/queries/sample20_equipment_evidence.ru) · [Virtuoso 실행 예시](https://docs.openlinksw.com/virtuoso/rdfindertmethodsparqlendpoint/)
