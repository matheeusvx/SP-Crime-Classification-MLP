"""Serviço de inferência: carrega uma vez o SafeClassifier e nada além dele.

Validação, normalização e One-Hot permanecem em ``final5.validation`` e no
pré-processador congelado; este módulo só adapta nomes para a interface.
"""
from collections.abc import Callable, Mapping
import logging
from pathlib import Path
import sys
import threading
from typing import Any

from .config import REPO_ROOT

logger = logging.getLogger('app.inference')

MESES = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto',
         'Setembro', 'Outubro', 'Novembro', 'Dezembro')
# Ordem definida pelo contrato seguro: segunda=0 ... domingo=6.
DIAS = ('Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo')


def _load_contract():
    src = str(REPO_ROOT/'src')
    if src not in sys.path:
        sys.path.insert(0, src)
    from final5.common import verify_manifest
    from final5.validation import SafeClassifier
    return SafeClassifier, verify_manifest


class ModelService:
    """Fachada thread-safe; o lock evita chamadas simultâneas ao modelo Keras."""

    def __init__(self, classifier: Any, manifest: Mapping[str, Any]):
        if manifest['threshold'] != 0.5 or manifest['calibration']['adopted'] is not False:
            raise ValueError('Manifesto incompatível: limiar ou calibração divergente do congelado.')
        self._classifier = classifier
        self._manifest = manifest
        self._lock = threading.Lock()
        self._vocabulary = classifier.validator.vocabulary()

    def classify(self, record: Any) -> dict[str, Any]:
        with self._lock:
            return self._classifier.classify(record)

    def options(self) -> dict[str, Any]:
        v = self._vocabulary
        return {
            'versao_contrato': v['versao_contrato'],
            'versao_modelo': v['versao_modelo'],
            'meses': [{'valor': m, 'rotulo': MESES[m-1]} for m in v['mes']],
            'dias_semana': [{'valor': d, 'rotulo': DIAS[d]} for d in v['dia_semana']],
            'tipos_local': v['tipo_local'],
            'bairros': v['bairro'],
            'ausencia_permitida': v['ausencia_permitida'],
        }

    def public_metadata(self) -> dict[str, Any]:
        m = self._manifest
        return {
            'versao_modelo': m['model_id'],
            'versao_contrato': self._vocabulary['versao_contrato'],
            'arquitetura': {
                'entradas': m['architecture']['input'],
                'camadas_ocultas': m['architecture']['hidden'],
                'ativacoes': m['architecture']['activations'],
                'parametros_treinaveis': m['architecture']['parameters'],
            },
            'limiar': m['threshold'],
            'probabilidades_calibradas': False,
            'rotulos': m['labels'],
            'atributos': m['features_order'],
            'colunas_por_atributo': {k: len(v) for k, v in m['feature_encoding_categories'].items()},
            'funcao_perda': m['loss'],
            'otimizador': m['optimizer'],
            'taxa_aprendizado': m['learning_rate'],
            'epocas': m['epochs'],
            'tamanho_lote': m['batch_size'],
            'linhas_ajuste_2023': m['preprocessing']['fit_rows'],
            'frequencia_minima_bairro': m['preprocessing']['min_count'],
            'bairros_com_coluna_propria': m['preprocessing']['retained_bairros'],
            'limitacoes': m['limitations'],
        }


def load_model_service(model_dir: Path | None = None) -> ModelService:
    SafeClassifier, verify_manifest = _load_contract()
    # SafeClassifier confere manifesto, hashes e dimensões antes de desserializar.
    classifier = SafeClassifier(model_dir) if model_dir else SafeClassifier()
    manifest = verify_manifest(classifier.validator.folder)
    return ModelService(classifier, manifest)


def try_load(factory: Callable[[], ModelService]) -> ModelService | None:
    """Sem artefatos válidos o processo sobe, mas nenhuma classificação é servida."""
    try:
        service = factory()
    except Exception:
        logger.exception('Modelo indisponível: classificações desativadas.')
        return None
    logger.info('Modelo congelado carregado e verificado.')
    return service
