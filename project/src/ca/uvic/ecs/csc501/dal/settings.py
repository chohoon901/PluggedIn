"""DAL-local configuration and path containment."""
from configparser import ConfigParser
from pathlib import Path


class Settings:
    def __init__(self, dal_root: Path | None = None):
        self.dal_root = (dal_root or Path(__file__).parent).resolve()
        config = ConfigParser()
        config.read(self.dal_root / 'config.properties', encoding='utf-8')
        self.database_path = self._within(config.get('sqlite', 'database_path', fallback='data/pluggedin.db'))
        self.metadata_path = self._within(config.get('sqlite', 'metadata_path', fallback='data/station_metadata.json'))
        self.busy_timeout_ms = config.getint('sqlite', 'busy_timeout_ms', fallback=5000)
        self.sparql_endpoint = config.get(
            'semantic', 'sparql_endpoint', raw=True, fallback='http://localhost:8890/sparql',
        )
        self.sparql_graph = config.get(
            'semantic', 'graph_iri', raw=True, fallback='https://github.com/chohoon901/PluggedIn/graph/',
        )
        if self.busy_timeout_ms < 0:
            raise ValueError('busy_timeout_ms must not be negative')
        if not config.getboolean('sqlite', 'foreign_keys', fallback=True):
            raise ValueError('foreign_keys must remain enabled')

    def _within(self, value):
        path = (self.dal_root / value).resolve()
        if not path.is_relative_to(self.dal_root):
            raise ValueError('Database paths must remain inside dal')
        return path
