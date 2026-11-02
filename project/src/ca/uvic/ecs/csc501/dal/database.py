from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .settings import Settings


class Database:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.engine = create_engine('sqlite:///' + self.settings.database_path.as_posix(),
                                    connect_args={'check_same_thread': False})

        @event.listens_for(self.engine, 'connect')
        def configure(connection, _):
            cursor = connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute(f'PRAGMA busy_timeout={self.settings.busy_timeout_ms}')
            cursor.close()

        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def health(self) -> bool:
        from .scripts.validate_db import validate_schema
        try:
            return self.settings.database_path.is_file() and not validate_schema(self)
        except Exception:
            return False
