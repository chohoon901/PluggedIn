"""경계를 잘못 넘는 import 및 원본 모델 누락을 탐지한다."""
import ast
from dataclasses import fields
from importlib import import_module
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "src" / "ca" / "uvic" / "ecs" / "csc501"
TABLES = ("organization", "site_owner", "operator", "network", "station", "connector_type", "port", "operating_period", "adapter", "vehicle", "vehicle_accepts", "driver", "membership")


def test_domain_and_presentation_dependencies_stay_inside_boundaries():
    for layer in ("cmn", "pl"):
        for path in (ROOT / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                imports = []
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imports = [node.module or ""]
                for name in imports:
                    components = name.split(".")
                    if layer == "cmn":
                        assert not set(components) & {"fastapi", "pydantic", "sqlalchemy", "sqlite3", "pathlib", "dal", "pl"}, (path, name)
                    else:
                        assert not set(components) & {"dal", "sqlalchemy", "sqlite3"}, (path, name)


def test_all_13_domain_entities_match_65_original_orm_columns():
    from ca.uvic.ecs.csc501.dal.models import Base
    assert len(Base.metadata.tables) == 13
    assert sum(len(table.columns) for table in Base.metadata.tables.values()) == 65
    for table_name in TABLES:
        module = import_module(f"ca.uvic.ecs.csc501.cmn.{table_name}")
        cls = getattr(module, "".join(part.title() for part in table_name.split("_")))
        names = {field.name for field in fields(cls)}
        if table_name == "vehicle":
            names.remove("vehicle_class")
            names.add("class")
        assert names == set(Base.metadata.tables[table_name].columns.keys()), table_name
