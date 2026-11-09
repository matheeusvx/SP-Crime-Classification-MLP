"""Contrato seguro 1.1.0: adaptador externo ao pipeline histórico congelado.

Não ajusta nem substitui normalização, vocabulário, pesos ou limiar.
"""
from collections.abc import Mapping
import numbers

from final5.common import FINAL, FEATURES, MODEL_ID, verify_manifest, sha256
from ml.preprocessing import MISSING

CONTRACT_VERSION = '1.1.0'
MANIFEST_SHA256 = 'b992412335c69623bdf63c9341cefaa82e0a81ae73d7d32e110f2498faa8c532'


class InputValidator:
    """Vocabulário proveniente somente do objeto ajustado em 2023."""

    def __init__(self, model_dir=FINAL):
        from pathlib import Path
        import joblib
        self.folder = Path(model_dir)
        manifest = verify_manifest(self.folder)
        if manifest['model_id'] != MODEL_ID or sha256(self.folder/'manifesto.json') != MANIFEST_SHA256:
            raise ValueError('Artefatos não correspondem à Dense64 final v1.0.0 aprovada.')
        self.preprocessor = joblib.load(self.folder/'preprocessador.joblib')
        if self.preprocessor.features != FEATURES or self.preprocessor.scope != 'completo_2023':
            raise ValueError('Esquema ou origem do vocabulário incompatível.')

    def vocabulary(self):
        """Opções para campos controlados; não é lista oficial de bairros."""
        pre = self.preprocessor
        return {
            'versao_contrato': CONTRACT_VERSION, 'versao_modelo': MODEL_ID,
            'mes': list(range(1, 13)), 'dia_semana': list(range(7)),
            'tipo_local': sorted(pre.known['tipo_local']),
            'bairro': [{'valor': name, 'grupo': 'frequente' if name in pre.frequent else 'raro'}
                       for name in sorted(pre.known['bairro'])],
            'ausencia_permitida': ['tipo_local', 'bairro'],
        }

    def validate(self, record):
        errors, warnings, groups = [], [], {}
        def error(field, code, message):
            errors.append({'campo': field, 'codigo': code, 'mensagem': message})
        if not isinstance(record, Mapping) or set(record) != set(FEATURES):
            error('entrada', 'esquema_invalido', 'Informe exatamente mes, dia_semana, tipo_local e bairro.')
            return {'valido': False, 'erros': errors, 'avisos': [], 'entrada': None, 'grupos': {}}
        values = dict(record)
        for field, lo, hi in [('mes', 1, 12), ('dia_semana', 0, 6)]:
            value = values[field]
            if not isinstance(value, numbers.Integral) or isinstance(value, bool) or not lo <= value <= hi:
                error(field, 'dominio_invalido', f'{field}: selecione um inteiro de {lo} a {hi}, não nulo.')
            else:
                values[field] = int(value)
        for field in ['tipo_local', 'bairro']:
            value = values[field]
            if value is None:
                groups[field] = 'ausente'
                warnings.append({'campo': field, 'codigo': 'ausente',
                                 'mensagem': 'Ausência explícita com exemplos no treinamento; interpretação limitada.'})
                continue
            if not isinstance(value, str) or not value.strip() or not any(c.isalpha() for c in value):
                error(field, 'categoria_invalida', 'Selecione uma categoria reconhecida ou ausência explícita (None).')
                continue
            try:
                # Usa o próprio objeto congelado: não inventar novas equivalências.
                probe = dict(mes=1, dia_semana=0, tipo_local=None, bairro=None)
                probe[field] = value
                canonical = self.preprocessor._raw(probe)[FEATURES.index(field)]
            except (ValueError, TypeError):
                error(field, 'categoria_invalida', 'Categoria reservada ou incompatível com o vocabulário.')
                continue
            if canonical == MISSING:
                error(field, 'ausencia_nao_explicita', 'Use a opção de ausência explícita, não texto sentinela.')
            elif canonical not in self.preprocessor.known[field]:
                groups[field] = 'desconhecido'
                error(field, 'categoria_desconhecida', 'Categoria não reconhecida. Escolha explicitamente uma opção do vocabulário.')
            else:
                values[field] = canonical
                groups[field] = 'raro' if field == 'bairro' and canonical not in self.preprocessor.frequent else 'reconhecido'
                if groups[field] == 'raro':
                    warnings.append({'campo': field, 'codigo': 'bairro_raro',
                                     'mensagem': 'Bairro reconhecido, representado pelo grupo compartilhado de raros; pode concentrar falsos positivos.'})
        return {'valido': not errors, 'erros': errors, 'avisos': warnings,
                'entrada': values if not errors else None, 'grupos': groups}


class SafeClassifier:
    """Ponto de entrada recomendado para novas integrações, sem HTTP ou datasets."""

    def __init__(self, model_dir=FINAL):
        from final5.pipeline import FinalPipeline
        self.validator = InputValidator(model_dir)
        self._pipeline = FinalPipeline(model_dir)

    def classify(self, record):
        validation = self.validator.validate(record)
        response = {'status': 'ok' if validation['valido'] else 'erro_validacao',
                    'versao_modelo': MODEL_ID, 'versao_contrato': CONTRACT_VERSION,
                    'probabilidades_calibradas': False, 'erros': validation['erros'],
                    'avisos': validation['avisos'], 'grupos': validation['grupos']}
        if not validation['valido']:
            return response  # Nenhuma chamada à rede em caso de erro.
        result = self._pipeline.classificar(**validation['entrada'])
        response.update(classe_estimada=result['classe_estimada'], codigo_classe=result['codigo_classe'],
                        scores_sigmoid={'furto': result['probabilidade_furto'], 'roubo': result['probabilidade_roubo']},
                        interpretacao_scores='Estimativas não calibradas de classificação; não são chance de crime futuro.')
        return response
