"""Fixtures: um único carregamento real do modelo congelado para toda a suíte."""
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.inference import load_model_service  # noqa: E402
from app.main import create_app  # noqa: E402

VALIDO = {'mes': 5, 'dia_semana': 2, 'tipo_local': 'VIA PÚBLICA', 'bairro': 'BELA VISTA'}


@pytest.fixture(scope='session')
def service():
    return load_model_service()


@pytest.fixture(scope='session')
def client(service):
    app = create_app(Settings(rate_limit_per_minute=100_000), service_factory=lambda: service)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def valido():
    return dict(VALIDO)
