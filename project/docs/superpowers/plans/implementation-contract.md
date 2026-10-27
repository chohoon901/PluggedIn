# 구현 공통 계약

기획서 원문 및 승인 설계가 우선한다. 패키지 약칭 P=`ca.uvic.ecs.csc501`.

## 공통 오류 — P.cmn.contracts.errors

AppError(message: str, code='INVALID_INPUT', status_code=400, field_errors: dict|None=None). 속성 message/code/status_code/field_errors.
InputError(message, field_errors=None):400, NotFoundError(message):404, ConflictError(message):409, NotReadyError(message):503.

## Entities

원문과 같은 필드 순서·이름. 각 entity는 P.cmn.<table>의 PascalCase 클래스(Organization, SiteOwner, Operator, Network, Station, ConnectorType, Port, OperatingPeriod, Adapter, Vehicle, VehicleAccepts, Driver, Membership).
Vehicle은 class 대신 vehicle_class. 금액 아닌 출력·좌표 Decimal, membership 날짜 date. DailyTime은 P.cmn.value_objects.daily_time, seconds:int, parse(str)->DailyTime, str()=HH:MM:SS. OperatingPeriod open_time/close_time은 DailyTime.

## 읽기 모델 — P.cmn.contracts.models

- VehicleSnapshot(vehicle:Vehicle, accepted_connector_ids:tuple[int,...]); accepts(id)->bool.
- StationMetadata(timezone:str|None=None, hours_completeness:str='UNKNOWN', ports_completeness:str='UNKNOWN', aggregate_completeness:str='INCOMPLETE', source_label:str='출처 미상', source_updated_at:str|None=None, unconfirmed_fields:tuple[str,...]=()).
- StationSnapshot(station:Station, ports:tuple[Port,...], operating_periods:tuple[OperatingPeriod,...], connector_types:tuple[ConnectorType,...], organizations:tuple[Organization,...], metadata:StationMetadata).

## 판정 — P.cmn.contracts.evaluation / P.cmn.services.evaluation

CheckStatus(str,Enum)=PASS/FAIL/UNKNOWN, OverallStatus=AVAILABLE/UNAVAILABLE/NEEDS_REVIEW, ReasonCode는 원문 §7.6.
Reason(code:ReasonCode, message:str).
CheckResult(status:CheckStatus, reasons:tuple[Reason,...], evidence:dict).
EvaluationResult(station_id:int, driver_id:int, vehicle_id:int, arrival_at:datetime, checks:dict[str,CheckResult], overall_status:OverallStatus, compatible_port_ids:tuple[int,...], selected_port_id:int|None, power_limit_kw:Decimal|None, warnings:tuple[Reason,...]).
EvaluationPolicy() 기본 정책 객체. evaluate_station(station:StationSnapshot, vehicle:VehicleSnapshot, memberships:list[Membership], arrival_at:datetime, policy:EvaluationPolicy|None=None, *, driver_id:int=1)->EvaluationResult.
aggregate_checks(statuses: iterable[CheckStatus])->OverallStatus.

## Repository/UoW — P.cmn.contracts.repositories

- DriverRepository: get(id)->Driver|None, list()->list[Driver], save(Driver)->Driver, delete(id)->None.
- VehicleRepository: get(id)->VehicleSnapshot|None, list()->list[VehicleSnapshot], save(Vehicle, accepted_connector_ids:list[int])->VehicleSnapshot, delete(id)->None.
- MembershipRepository: get(id)->Membership|None, list(driver_id:int|None=None)->list[Membership], save(Membership)->Membership, delete(id)->None.
- StationRepository: get(id)->StationSnapshot|None, list()->list[StationSnapshot].
- CatalogRepository: connectors()->list[ConnectorType], networks()->list[Organization].
- OrganizationRepository: get(id)->Organization|None, list()->list[Organization].
- UnitOfWork context manager: drivers/vehicles/memberships/stations/catalog/organizations; commit(), rollback(). __exit__ rollback on failure and close. DAL converts integrity errors to ConflictError, missing schema/connect failures to NotReadyError.

## DAL public entrypoints

- P.dal.settings.Settings(dal_root:Path|None=None): .database_path, .metadata_path. Default package dal directory; custom test dal_root permitted. Config path must remain within this root.
- P.dal.database.Database(settings:Settings|None=None): .engine, .session_factory, .settings, health()->bool; no automatic schema creation.
- P.dal.unit_of_work.SqlAlchemyUnitOfWork(database:Database).
- P.dal.scripts.init_db.init_database(database:Database|None=None)->None.
- P.dal.scripts.seed_demo.seed_demo(database:Database|None=None)->None.
- P.dal.scripts.validate_db.validate_database(database:Database|None=None)->list[str] (empty=valid). Modules executable using python -m.

## ApplicationService — P.cmn.application.services (root agent owns)

ApplicationService(uow_factory:Callable[[],UnitOfWork], health_check:Callable[[],bool]). No DAL import.
All outputs below are Python dict/list of JSON primitives; Decimal converted to numeric, date/datetime ISO strings, enums values. Input validated here as well as DTO.

- list_drivers()->list[dict], get_driver(id)->dict, save_driver(data:dict, driver_id:int|None=None)->dict, delete_driver(id)->None.
- list_vehicles/get_vehicle/save_vehicle(data,vehicle_id=None)/delete_vehicle same pattern; accepted_connector_ids sorted list.
- list_memberships(driver_id=None)/get_membership/save_membership(data,membership_id=None)/delete_membership same pattern.
- catalog()->{'connectors':[{connector_type_id,name,max_power_kw}], 'networks':[{organization_id,name,website}]}.
- health()->bool.
- search(driver_id:int, vehicle_id:int, arrival_at:str|datetime|None, bbox:dict, status:str='ALL')->dict. Result {driver_id,vehicle_id,arrival_at,evaluation_at,results:list[dict],counts:{AVAILABLE,NEEDS_REVIEW,UNAVAILABLE}}. Counts before status filter.
- detail(station_id:int,driver_id:int,vehicle_id:int,arrival_at:str|datetime|None)->dict.
- Each result entry is EvaluationResult fields plus station dict (original fields), ports list, operating_periods list, organizations list, source dict (timezone,hours_completeness,ports_completeness,aggregate_completeness,source_label,source_updated_at,unconfirmed_fields). Each check serialized {status,reasons:[{code,message}],evidence}. Detail returns same entry. Ports include connector_name for display.
- current_instant()->str aware UTC string. May be module function; pages use one generated string for initial form. search/detail called with empty arrival choose now exactly once.

## Presentation public entrypoints

P.pl.dependencies.get_services(request:Request)->ApplicationService uses request.app.state.services.
P.pl.routes.__init__.router:APIRouter includes all routers.
P.pl.error_handlers.register_error_handlers(app:FastAPI).
P.pl.schemas validates input with Pydantic then services enforce same rules. Form route db work runs in def handlers; use Form fields, no asyncio database calls.
Main (root owns): create_app(database=None)->FastAPI, constructs ApplicationService with lambda:SqlAlchemyUnitOfWork(database), app.state.services. Mount only pl/static.
