"""Configuração por ambiente; nenhum caminho específico de máquina."""
from dataclasses import dataclass, field
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ORIGINS = ('http://localhost:5173', 'http://127.0.0.1:5173')


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError(f'{name} deve ser positivo')
    return value


def _origins() -> tuple[str, ...]:
    raw = os.environ.get('CORS_ORIGINS')
    if raw is None:
        return DEFAULT_ORIGINS
    origins = tuple(item.strip().rstrip('/') for item in raw.split(',') if item.strip())
    if '*' in origins:
        raise ValueError('CORS_ORIGINS não aceita curinga; liste as origens autorizadas')
    return origins


@dataclass(frozen=True)
class Settings:
    app_env: str = 'development'
    cors_origins: tuple[str, ...] = DEFAULT_ORIGINS
    rate_limit_per_minute: int = 60
    max_body_bytes: int = 2048
    model_dir: Path | None = None  # None = pasta congelada padrão do contrato seguro
    data_dir: Path = field(default=BACKEND_DIR/'data')
    frontend_dist: Path | None = None

    @property
    def expose_docs(self) -> bool:
        return self.app_env == 'development'


def load_settings() -> Settings:
    model_dir = os.environ.get('MODEL_DIR')
    dist = os.environ.get('FRONTEND_DIST')
    resolved_dist = Path(dist) if dist else REPO_ROOT/'web/frontend/dist'
    return Settings(
        app_env=os.environ.get('APP_ENV', 'development'),
        cors_origins=_origins(),
        rate_limit_per_minute=_positive_int('RATE_LIMIT_PER_MINUTE', 60),
        max_body_bytes=_positive_int('MAX_BODY_BYTES', 2048),
        model_dir=Path(model_dir) if model_dir else None,
        data_dir=Path(os.environ.get('DATA_DIR', BACKEND_DIR/'data')),
        frontend_dist=resolved_dist if (resolved_dist/'index.html').is_file() else None,
    )
