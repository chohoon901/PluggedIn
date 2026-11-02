"""DAL-local configuration and path containment."""
from configparser import ConfigParser
from pathlib import Path


class Settings:
    def __init__(self, dal_root: Path | None = None):
        self.dal_root = (dal_root or Path(__file__).parent).resolve()
        config = ConfigParser()
        config.read(self.dal_root / 'config.properties', encoding='utf-8')
        self.database_path = self._within(config.get('sqlite', 'database_path', fallback='data/pluggedin.db'))
        self.metadata_path = self._within('data/station_metadata.json')
        self.busy_timeout_ms = config.getint('sqlite', 'busy_timeout_ms', fallback=5000)
        if self.busy_timeout_ms < 0:
            raise ValueError('busy_timeout_ms must not be negative')
        if not config.getboolean('sqlite', 'foreign_keys', fallback=True):
            raise ValueError('foreign_keys must remain enabled')

    def _within(self, value):
        path = (self.dal_root / value).resolve()
        if not path.is_relative_to(self.dal_root):
            raise ValueError('Database paths must remain inside dal')
        return path
