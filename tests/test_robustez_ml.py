"""Etapa 3: entradas adversas, invariantes, diagnosticos e preservacao."""
import sys,json,pickle,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from diagnostics.common import *
from ml.inference import ClassificadorOcorrencias
from ml.dataset import load_year
from ml.preprocessing import MISSING,RARE
from unittest.mock import patch

class Robustez(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.clf=ClassificadorOcorrencias();cls.pre=cls.clf.preprocessador
    def test_probabilidades_e_limiar(self):
        for row in [(5,2,'VIA PÚBLICA','BELA VISTA'),(1,0,None,None),(None,None,None,None),(12,6,'NOVO LOCAL','NOVO BAIRRO')]:
            r=self.clf.classificar(*row);p=r['probabilidade_roubo']
            self.assertTrue(np.isfinite(p));self.assertTrue(0<=p<=1)
            self.assertAlmostEqual(r['probabilidade_furto']+p,1,places=12)
            self.assertEqual(r['codigo'],int(p>=.5))
    def test_repeticao_exata(self):
        args=(5,2,'VIA PÚBLICA','BELA VISTA')
        self.assertEqual(self.clf.classificar(*args),self.clf.classificar(*args))
    def test_caixa_espacos_unicode(self):
        import unicodedata
        a=self.clf.classificar(5,2,'VIA PÚBLICA','BRÁS')
        b=self.clf.classificar(5,2,unicodedata.normalize('NFD',' via pública '),' brás ')
        self.assertEqual(a,b)
    def test_alias_bairro_inspecionado(self):
        self.assertEqual(self.clf.classificar(5,2,'VIA PÚBLICA','BRÁS'),self.clf.classificar(5,2,'VIA PÚBLICA','BRAS'))
    def test_acento_local_baseline_historico_nao_e_equivalencia_automatica(self):
        # Escopo: baseline da Etapa 2. O final local_alias=True tem outro contrato,
        # coberto em test_contrato_inferencia_seguro, sem alterar este artefato.
        r=dict(mes=5,dia_semana=2,tipo_local='VIA PUBLICA',bairro='BELA VISTA')
        active=[self.pre.feature_names_[i] for i in self.pre.transform([r]).indices]
        self.assertIn('tipo_local_'+MISSING,active)
    def test_categoria_rara_e_nova(self):
        known=next(k for k in self.pre.known_bairros_ if k not in self.pre.frequent_bairros_)
        common=dict(mes=5,dia_semana=2,tipo_local='VIA PÚBLICA')
        a=self.pre.transform([common|{'bairro':known}]);b=self.pre.transform([common|{'bairro':'BAIRRO NUNCA VISTO'}])
        self.assertEqual((a!=b).nnz,0)
    def test_ausencias_textuais(self):
        common=dict(mes=5,dia_semana=2,bairro=None)
        a=self.pre.transform([common|{'tipo_local':None}])
        for s in ['','  ','NULL','N/A','nan']:
            self.assertEqual((a!=self.pre.transform([common|{'tipo_local':s}])).nnz,0)
    def test_numeros_fora_dominio(self):
        for mes,dia in [(0,1),(13,2),(1,-1),(1,7),(-10,2)]:
            with self.assertRaises(ValueError):self.clf.classificar(mes,dia,None,None)
    def test_tipos_incompativeis(self):
        for mes,dia,local,bairro in [('5',2,None,None),(5.0,2,None,None),(True,2,None,None),(5,2.0,None,None),(5,2,12,None),(5,2,None,152),(float('nan'),2,None,None),(float('inf'),2,None,None)]:
            with self.assertRaises((TypeError,ValueError)):self.clf.classificar(mes,dia,local,bairro)
    def test_esquema_estrito(self):
        r=dict(mes=5,dia_semana=2,tipo_local=None,bairro=None)
        for col in ['periodo_fato','alvo','chave_bo','RUBRICA']:
            with self.assertRaises(ValueError):self.pre.transform([r|{col:'proibido'}])
    def test_inferencia_sem_datasets(self):
        original=Path.open
        def restricted(path,*args,**kwargs):
            if 'data' in path.parts:raise AssertionError('Inferencia tentou abrir dataset')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',restricted):
            loaded=ClassificadorOcorrencias();r=loaded.classificar(5,2,None,None)
            self.assertTrue(np.isfinite(r['probabilidade_roubo']))
    def test_preprocessador_congelado(self):
        before=pickle.dumps(self.pre)
        self.clf.classificar(12,6,'LOCAL NOVO','BAIRRO NOVO')
        self.assertEqual(before,pickle.dumps(self.pre));self.assertEqual(self.pre.fit_year_,2023)
    def test_artefatos_preservados(self):
        from maintenance56.integrity import verify_history
        self.assertGreater(verify_history(read('preservacao.json')),0)
    def test_reserva_2025(self):
        with self.assertRaises(ValueError):load_year(None,2025)
        a=read('acesso_dados.json')
        self.assertEqual(a['diagnostic_years'],[2023,2024]);self.assertEqual(a['test_2025_predictions'],0);self.assertEqual(a['test_2025_transformations'],0)
    def test_matriz_reproduzida(self):
        m=read('resumo.json')['validacao']
        self.assertEqual([m[k] for k in ['tn','fp','fn','tp']],[68328,23727,25962,40878])
        self.assertEqual(m['fp']+m['fn'],49689)
    def test_metricas_calibracao_validas(self):
        r=read('resumo.json')
        self.assertTrue(0<=r['brier']<=1);self.assertTrue(0<=r['ece_10']<=1);self.assertGreaterEqual(r['log_loss'],0)
    def test_repeticoes_mesma_arquitetura(self):
        for seed in [42,7,123]:
            r=read(f'estabilidade_{seed}.json');c=r['config']
            self.assertEqual(c['units'],[64,1]);self.assertEqual(c['input'],299);self.assertEqual(c['learning_rate'],.001)
            self.assertEqual(c['batch_size'],256);self.assertEqual(c['train_year'],2023);self.assertEqual(c['validation_year'],2024)
            self.assertEqual(c['preprocessor_sha256'],sha256(MODELS/'preprocessador.joblib'))
        self.assertTrue(read('estabilidade_42.json')['baseline_reproduced_atol_1e7'])

if __name__=='__main__':unittest.main(verbosity=2)
