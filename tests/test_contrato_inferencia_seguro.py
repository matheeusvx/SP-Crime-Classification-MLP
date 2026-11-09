"""Regressão 5.6: exemplos sintéticos e artefatos; sem inferência em datasets."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import unittest
from unittest.mock import patch
import json
import pickle
import math
from final5.validation import InputValidator, SafeClassifier, CONTRACT_VERSION, MANIFEST_SHA256
from final5.common import FINAL, MODEL_ID, verify_manifest, sha256


class ContratoSeguro(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clf = SafeClassifier()
        cls.validator = cls.clf.validator
        cls.valid = dict(mes=5, dia_semana=2, tipo_local='VIA PÚBLICA', bairro='BELA VISTA')

    def rejected_without_inference(self, record):
        with patch.object(self.clf._pipeline, 'classificar', side_effect=AssertionError('Inferência indevida')):
            response = self.clf.classify(record)
        self.assertEqual(response['status'], 'erro_validacao')
        self.assertTrue(response['erros'])
        self.assertNotIn('scores_sigmoid', response)
        self.assertNotIn('classe_estimada', response)
        json.dumps(response, allow_nan=False)
        return response

    def test_mes_obrigatorio(self):
        for value in [None, 0, 13, -1, '5', 5.0, True, float('nan'), float('inf')]:
            with self.subTest(value=value): self.rejected_without_inference(self.valid|{'mes': value})

    def test_dia_dominio_real(self):
        self.assertEqual(self.validator.vocabulary()['dia_semana'], list(range(7)))
        for value in [None, -1, 7, '2', 2.0, False, float('nan')]:
            with self.subTest(value=value): self.rejected_without_inference(self.valid|{'dia_semana': value})

    def test_extremos_calendario(self):
        for month in [1, 12]:
            for day in [0, 6]: self.assertTrue(self.validator.validate(self.valid|{'mes': month, 'dia_semana': day})['valido'])

    def test_local_desconhecido(self):
        r = self.rejected_without_inference(self.valid|{'tipo_local': 'PRAIA'})
        self.assertEqual(r['erros'][0]['codigo'], 'categoria_desconhecida')

    def test_bairro_desconhecido(self):
        r = self.rejected_without_inference(self.valid|{'bairro': 'BAIRRO NUNCA OBSERVADO XYZ'})
        self.assertEqual(r['grupos']['bairro'], 'desconhecido')

    def test_bairro_sem_letras(self):
        for value in ['123', '１２３', '!!!', '12-34', '', '   ', 123, [], {}]:
            with self.subTest(value=value): self.rejected_without_inference(self.valid|{'bairro': value})

    def test_sentinelas_nao_viram_ausencia_silenciosa(self):
        for field in ['bairro', 'tipo_local']:
            for value in ['NULL', 'N/A', 'nan', '__AUSENTE__', '']:
                with self.subTest(field=field, value=value): self.rejected_without_inference(self.valid|{field: value})

    def test_tipo_local_incompativel(self):
        for value in [True, 12, [], {}, 3.5]: self.rejected_without_inference(self.valid|{'tipo_local': value})

    def test_esquema_estrito(self):
        for value in [None, [], 'entrada', {}, self.valid|{'alvo': 1}, {k:v for k,v in self.valid.items() if k!='mes'}]:
            self.rejected_without_inference(value)

    def test_varios_erros(self):
        r = self.rejected_without_inference(dict(mes=None, dia_semana=None, tipo_local='PRAIA', bairro='123'))
        self.assertEqual(len(r['erros']), 4)

    def test_ausencia_local_explicita(self):
        r = self.clf.classify(self.valid|{'tipo_local': None})
        self.assertEqual(r['status'], 'ok'); self.assertEqual(r['grupos']['tipo_local'], 'ausente')
        self.assertTrue(any(w['campo']=='tipo_local' for w in r['avisos']))

    def test_ausencia_bairro_explicita(self):
        r = self.clf.classify(self.valid|{'bairro': None})
        self.assertEqual(r['status'], 'ok'); self.assertEqual(r['grupos']['bairro'], 'ausente')

    def test_bairro_raro_reconhecido(self):
        pre = self.validator.preprocessor
        rare = sorted(pre.known['bairro']-pre.frequent)[0]
        r = self.clf.classify(self.valid|{'bairro': rare})
        self.assertEqual(r['grupos']['bairro'], 'raro')
        self.assertIn('bairro_raro', [w['codigo'] for w in r['avisos']])

    def test_bairro_frequente(self):
        self.assertEqual(self.clf.classify(self.valid)['grupos']['bairro'], 'reconhecido')

    def test_alias_local_final(self):
        self.assertEqual(self.clf.classify(self.valid), self.clf.classify(self.valid|{'tipo_local': ' via publica '}))

    def test_alias_bairro_verificado(self):
        a = self.clf.classify(self.valid|{'bairro': 'BRÁS'})
        b = self.clf.classify(self.valid|{'bairro': ' bras '})
        self.assertEqual(a, b)

    def test_nao_inventa_equivalencia_bairros(self):
        pre = self.validator.preprocessor
        a = self.validator.validate(self.valid|{'bairro':'TATUAPE'})
        b = self.validator.validate(self.valid|{'bairro':'TATUAPÉ'})
        self.assertEqual(a['entrada']['bairro'], pre._raw(self.valid|{'bairro':'TATUAPE'})[3])
        self.assertEqual(b['entrada']['bairro'], pre._raw(self.valid|{'bairro':'TATUAPÉ'})[3])
        self.assertNotEqual(a['entrada']['bairro'], b['entrada']['bairro'])

    def test_acento_nao_reconhecido_exige_escolha(self):
        # O histórico transformava esta grafia desconhecida em rara. Não
        # confundir essa possibilidade técnica com presença no vocabulário.
        self.assertTrue(self.validator.validate(self.valid|{'bairro':'JARDIM ANGELA'})['valido'])
        self.rejected_without_inference(self.valid|{'bairro':'JARDIM ÂNGELA'})

    def test_vocabulario_exclusivo_treino(self):
        pre = self.validator.preprocessor; v = self.validator.vocabulary()
        self.assertEqual(set(v['tipo_local']), pre.known['tipo_local'])
        self.assertEqual({r['valor'] for r in v['bairro']}, pre.known['bairro'])
        self.assertEqual(pre.scope, 'completo_2023'); self.assertEqual(pre.rows, 190124)
        self.assertEqual(v['ausencia_permitida'], ['tipo_local', 'bairro'])

    def test_todas_opcoes_sao_aceitas(self):
        v = self.validator.vocabulary()
        for field in ['tipo_local', 'bairro']:
            for item in v[field]:
                value = item['valor'] if isinstance(item, dict) else item
                self.assertTrue(self.validator.validate(self.valid|{field:value})['valido'], field)

    def test_outros_nao_e_ausente(self):
        a=self.validator.validate(self.valid|{'tipo_local':'OUTROS'})
        b=self.validator.validate(self.valid|{'tipo_local':None})
        self.assertNotEqual(a['entrada']['tipo_local'], b['entrada']['tipo_local'])

    def test_versao_correta_nao_baseline(self):
        self.assertEqual(self.clf._pipeline.manifest['model_id'], MODEL_ID)
        self.assertEqual(self.clf._pipeline.manifest['source_run'], 'B64_full_s42')
        self.assertEqual(self.clf._pipeline.model.count_params(), 19265)
        self.assertEqual(sha256(FINAL/'manifesto.json'), MANIFEST_SHA256)
        source=(ROOT/'src/final5/validation.py').read_text(encoding='utf-8')
        self.assertNotIn('from ml.inference', source)

    def test_scores_integridade_e_limiar(self):
        r=self.clf.classify(self.valid); p=r['scores_sigmoid']['roubo']
        self.assertTrue(math.isfinite(p)); self.assertTrue(0<=p<=1)
        self.assertAlmostEqual(sum(r['scores_sigmoid'].values()), 1)
        self.assertEqual(r['codigo_classe'], int(p>=.5))
        self.assertEqual(r['classe_estimada'], 'ROUBO' if p>=.5 else 'FURTO')
        self.assertFalse(r['probabilidades_calibradas']); self.assertEqual(r['versao_contrato'], CONTRACT_VERSION)
        self.assertEqual(json.loads(json.dumps(r,allow_nan=False)),r)

    def test_sem_mudanca_inferencia_valida(self):
        old=self.clf._pipeline.classificar(**self.valid);new=self.clf.classify(self.valid)
        self.assertEqual(new['scores_sigmoid']['roubo'], old['probabilidade_roubo'])
        self.assertEqual(new['classe_estimada'], old['classe_estimada'])

    def test_determinismo(self):
        self.assertEqual(self.clf.classify(self.valid), self.clf.classify(self.valid))

    def test_sem_mutacao_preprocessador(self):
        pre=self.validator.preprocessor;before=pickle.dumps(pre)
        self.validator.validate(self.valid);self.validator.vocabulary()
        self.assertEqual(before,pickle.dumps(pre))

    def test_sem_acesso_datasets(self):
        original=Path.open
        def guarded(path,*args,**kwargs):
            if 'data' in path.parts or path.suffix in {'.npz','.parquet'}:
                raise AssertionError('Contrato acessou dados históricos')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guarded):
            self.assertEqual(SafeClassifier().classify(self.valid)['status'],'ok')

    def test_artefatos_e_fontes_congeladas(self):
        verify_manifest()
        self.assertEqual(sha256(FINAL/'modelo.keras'),'dadad1326e6ae58d0f26f7e69638a9283d46863c9ecb7d56e76e037b4940091c')
        self.assertEqual(sha256(FINAL/'preprocessador.joblib'),'b8b3cd3662505b872b5e6d34296fba53a5b1ce5e065811d128f0423aa050a524')

    def test_manifesto_preservado_e_sem_calibrador(self):
        self.assertEqual(sha256(FINAL/'manifesto.json'),MANIFEST_SHA256)
        self.assertFalse((FINAL/'calibrador.joblib').exists())

    def test_snapshot_e_revisoes(self):
        from maintenance56.integrity import verify_snapshot
        self.assertGreater(verify_snapshot(), 344)


if __name__=='__main__': unittest.main(verbosity=2)
