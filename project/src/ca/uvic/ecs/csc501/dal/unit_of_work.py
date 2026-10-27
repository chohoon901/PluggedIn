from sqlalchemy.exc import IntegrityError, OperationalError, DatabaseError
from ca.uvic.ecs.csc501.cmn.contracts.errors import ConflictError, NotReadyError
from .repositories import DriverRepository, VehicleRepository, MembershipRepository, StationRepository, CatalogRepository, OrganizationRepository
from .validation import aggregate_issues


class SqlAlchemyUnitOfWork:
    def __init__(self, database):
        self.database = database
        self.session = None
        self.metadata_override = None

    def __enter__(self):
        if not self.database.health():
            raise NotReadyError('Initialize the database first.')
        self.session = self.database.session_factory()
        self.drivers = DriverRepository(self.session)
        self.vehicles = VehicleRepository(self.session)
        self.memberships = MembershipRepository(self.session)
        self.stations = StationRepository(self.session, self.database.settings)
        self.catalog = CatalogRepository(self.session)
        self.organizations = OrganizationRepository(self.session)
        return self

    def commit(self):
        try:
            self.session.flush()
            issues = aggregate_issues(self.session, self.database.settings, self.metadata_override)
            if issues:
                raise ConflictError('; '.join(issues))
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ConflictError('Check for duplicate values or data relationship and range constraints.') from error
        except (OperationalError, DatabaseError) as error:
            self.session.rollback()
            raise NotReadyError('The database could not be accessed.') from error
        except Exception:
            self.session.rollback()
            raise

    def rollback(self):
        if self.session is not None:
            self.session.rollback()

    def __exit__(self, exception_type, exception, traceback):
        try:
            self.rollback()
        finally:
            self.session.close()
        if isinstance(exception, IntegrityError):
            raise ConflictError('Check for duplicate values or data relationship and range constraints.') from exception
        if isinstance(exception, (OperationalError, DatabaseError)):
            raise NotReadyError('The database could not be accessed.') from exception
        return False
