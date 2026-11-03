"""Portable selected-source fixtures: no dependency on untracked full downloads."""
import csv
import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_sources(tmp_path):
    manifest_path = (Path(__file__).resolve().parents[1] / 'src/ca/uvic/ecs/csc501/dal/data/sample20/source_manifest.json')
    stations = json.loads(manifest_path.read_text(encoding='utf-8'))['stations']
    csv_path, ocm_path = tmp_path / 'nlr.csv', tmp_path / 'ocm.json'
    with csv_path.open('w', encoding='cp1252', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stations[0]['nlr']))
        writer.writeheader()
        writer.writerows(item['nlr'] for item in stations)
    ocm_path.write_text(json.dumps([item['ocm'] for item in stations]), encoding='utf-8')
    return csv_path, ocm_path
