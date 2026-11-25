# PluggedIn 팀원용 로컬 실행 가이드

이 가이드는 Windows와 macOS에서 각자의 Virtuoso로 PluggedIn을 실행하는 방법을 안내합니다. 저장소의 `main` 브랜치를 사용합니다. 저장소에 포함된 `sample20` SQLite 파일과 충전소 메타데이터로 시연용 그래프를 만듭니다.

## 1. 프로젝트와 Virtuoso 준비

### 필요한 프로그램 설치

Git과 Python 3.12 이상을 설치합니다. Windows에서는 PowerShell, macOS에서는 Terminal을 새로 열고 `git --version`을 실행해 Git이 설치됐는지 확인합니다. Python은 Windows에서 `py -3 --version`, macOS에서 `python3 --version`으로 확인합니다. Windows에 `py`가 없으면 `python --version`을 사용합니다. [Git 설치](https://git-scm.com/install/) · [Python 설치](https://www.python.org/downloads/)

Windows에서는 설치 프로그램을 사용하고, Homebrew를 사용하는 macOS에서는 `brew install virtuoso`를 실행해 로컬 Virtuoso 서버를 설치합니다. 2단계와 4단계에서 Virtuoso 관리자 계정으로 로그인합니다. [Virtuoso 다운로드](https://vos.openlinksw.com/owiki/wiki/VOS/VOS/VOSDownload) · [Homebrew 설치](https://brew.sh/) · [Virtuoso Homebrew 패키지](https://formulae.brew.sh/formula/virtuoso)

### 저장소 받기

처음 받는 경우, 프로젝트를 저장할 폴더에서 아래 명령을 실행합니다.

```text
git clone --branch main https://github.com/chohoon901/PluggedIn.git
cd PluggedIn
cd project
```

이미 `main`을 추적하는 저장소가 있다면 저장소 루트에서 `git pull --ff-only`를 실행한 뒤 `cd project`로 이동합니다. 이후 앱 명령은 이 터미널의 `project/` 폴더에서 실행합니다.

### Virtuoso 시작

- **Windows.** 설치 프로그램으로 서비스를 등록했다면 Windows **서비스** 앱에서 OpenLink Virtuoso를 시작합니다. 터미널에서 실행하려면 `virtuoso.ini`가 들어 있는 Virtuoso 데이터베이스 폴더에서 별도의 PowerShell을 열고 `& ..\bin\virtuoso-t.exe -f -c virtuoso.ini`를 실행합니다. 설치 방식에 따라 실행 파일 이름은 `virtuoso-odbc-t.exe`일 수 있습니다. [OpenLink Windows 설정](https://vos.openlinksw.com/owiki/wiki/VOS/VOSUsageWindows)
- **macOS.** 별도의 Terminal에서 설치한 `virtuoso.ini`의 위치를 찾습니다. Homebrew로 설치했다면 `brew list virtuoso | grep '/virtuoso.ini$'`로 설정 파일 위치를 확인할 수 있습니다. 파일이 있는 폴더로 이동해 `virtuoso-t -f -c virtuoso.ini`를 실행합니다. [Virtuoso 서버 설정](https://docs.openlinksw.com/virtuoso/ch-server/)

Virtuoso를 실행한 상태에서 [로컬 SPARQL 편집기](http://127.0.0.1:8890/sparql)를 열어 접속을 확인합니다. 포트가 다르면 `virtuoso.ini`의 `[HTTPServer]`에 설정된 포트를 사용합니다. 온톨로지 업로드와 앱 연결에는 같은 Virtuoso 인스턴스를 사용합니다.

## 2. 앱 전용 그래프 준비

**이미 이 가이드의 이관 명령으로 앱 그래프를 만들었다면** 기존 그래프와 계정을 사용합니다. 3단계에서 연결을 설정한 뒤 4단계의 **기존 앱 그래프** 명령을 실행합니다.

**예전에 RDF 파일만 업로드했거나 이번이 첫 실행이라면** 앱용 그래프를 준비합니다. 기존 RDF를 올린 기본 그래프는 `https://github.com/chohoon901/PluggedIn/graph/`입니다. 앱 그래프의 기본 이름은 다음과 같습니다.

```text
https://github.com/chohoon901/PluggedIn/graph/app/
```

이미 앱 그래프 이름에 수동으로 RDF를 올려둔 경우, 빈 그래프 이름을 새로 정합니다. 설정 파일의 `app_graph_iri`와 아래 SQL의 앱 그래프 이름을 둘 다 새 이름으로 바꾸면 기존 RDF를 보관하면서 이관할 수 있습니다. [config.properties](../src/ca/uvic/ecs/csc501/dal/config.properties)

앱용 로컬 Virtuoso에서 관리자 계정(일반적으로 `dba`)으로 **Conductor → Interactive SQL**을 열거나 Virtuoso의 `isql`로 접속합니다. `isql`에는 `virtuoso.ini`의 `[Parameters]`에 설정된 SQL 포트(기본 `1111`)를 사용합니다. Windows에서는 Virtuoso 설치 폴더의 `bin/isql.exe`, macOS Homebrew 환경에서는 `$(brew --prefix virtuoso)/bin/isql`을 사용합니다. [Interactive SQL 접속 옵션](https://docs.openlinksw.com/virtuoso/virtuoso_clients_isql/)

아래 예시의 `YOUR_LOCAL_PASSWORD`를 이 PC에서 사용할 앱 계정의 암호로 바꿔 실행합니다. `pluggedin_app` 계정이 이미 있으면 첫 줄은 건너뜁니다.

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

운영체제에 맞는 명령을 실행합니다. Virtuoso HTTP 포트가 다르면 `PLUGGEDIN_VIRTUOSO_ORIGIN`의 `8890`을 바꿉니다. 예를 들어 Virtuoso를 `8893`으로 열었다면 `http://127.0.0.1:8893`을 사용합니다. 가상환경의 Python이 3.12 이상인지 확인합니다. 2단계에서 정한 `pluggedin_app` 비밀번호를 입력하고, 이후 명령도 **같은 터미널**에서 실행합니다.

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



### 온톨로지(TBox) 적재

처음 실행할 때 [PluggedIn.rdf](../src/ca/uvic/ecs/csc501/dal/semantic/PluggedIn.rdf)를 아래 온톨로지 그래프에 올립니다. 다음 단계에서 샘플 데이터를 이관할 앱 그래프는 비어 있어야 합니다.

```text
https://github.com/chohoon901/PluggedIn/graph/schema/
```

**Conductor가 있는 경우.** 사용하는 Virtuoso의 `http://127.0.0.1:8890/conductor`를 열고 관리자 계정으로 로그인합니다. **Linked Data → Quad Store Upload → File**에서 `PluggedIn.rdf`를 선택합니다. **Named Graph IRI**에 위 스키마 그래프 주소를 붙여넣고 **Upload**를 누릅니다. `Upload finished` 메시지가 뜨고 **Linked Data → Graphs**에 그래프가 표시되는지 확인합니다.

**Conductor가 없는 경우.** Windows PowerShell에서 `project/` 폴더로 이동한 뒤 아래 명령을 실행합니다. macOS에서는 `curl.exe`를 `curl`로 바꿉니다. 사용하는 Virtuoso의 HTTP 포트가 다르면 주소의 포트를 바꾸고, 관리자 계정 이름이 다르면 `dba`를 바꿉니다. 비밀번호 입력 창이 뜨면 관리자 계정의 비밀번호를 입력합니다. [Virtuoso 그래프 업로드 주소 안내](https://docs.openlinksw.com/virtuoso/rdfsparqlprotocolendpoint/)

```powershell
curl.exe --anyauth --user dba --fail --silent --show-error --write-out "HTTP %{http_code}\n" --request POST --header "Content-Type: application/rdf+xml" --data-binary "@src/ca/uvic/ecs/csc501/dal/semantic/PluggedIn.rdf" "http://127.0.0.1:8890/sparql-graph-crud-auth?graph-uri=https%3A%2F%2Fgithub.com%2Fchohoon901%2FPluggedIn%2Fgraph%2Fschema%2F"
```

**TBox 확인.** 같은 인스턴스의 SPARQL 편집기 `http://127.0.0.1:8890/sparql`을 엽니다. **Query Text**에 아래 쿼리를 붙여넣고 **Execute Query**를 누릅니다. 온톨로지를 이미 올렸다면 이 쿼리로 확인한 뒤 다음 단계로 진행합니다.

```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?type (COUNT(DISTINCT ?entity) AS ?count)
WHERE {
    GRAPH <https://github.com/chohoon901/PluggedIn/graph/schema/> {
        ?entity a ?type .
        FILTER (?type IN (owl:Class, owl:ObjectProperty, owl:DatatypeProperty))
    }
}
GROUP BY ?type
```

결과는 **OWL 클래스 12개, 객체 속성 11개, 데이터 속성 40개**입니다. 온톨로지는 `graph/schema/`에 저장하고, 샘플 인스턴스 데이터는 비공개 `graph/app/`에 이관합니다.

Conductor로 온톨로지를 올리고 선언 건수를 확인하는 절차는 macOS의 Virtuoso 07.20.3243에서 검증했습니다.

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

