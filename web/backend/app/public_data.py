"""Agregados pré-computados; carregados uma vez, sem acesso a Parquet ou planilhas."""
import json
import logging
from pathlib import Path
from typing import Any

from .schemas import Estatisticas

logger = logging.getLogger('app.public_data')


def load_statistics(data_dir: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads((data_dir/'estatisticas.json').read_text(encoding='utf-8'))
        return Estatisticas.model_validate(raw).model_dump()
    except Exception:
        logger.exception('Estatísticas agregadas indisponíveis.')
        return None


def load_methodology(data_dir: Path) -> dict[str, Any] | None:
    try:
        return json.loads((data_dir/'metodologia.json').read_text(encoding='utf-8'))
    except Exception:
        logger.exception('Dados de metodologia indisponíveis.')
        return None
