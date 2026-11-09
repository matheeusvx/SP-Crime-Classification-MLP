"""Testes previos sem inferencia2025 e testes posteriores somente de resultados salvos."""
import sys,unittest,json,pickle,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from final5.common import *
from final5.pipeline import FinalPipeline
from final5.metrics import metrics,confidence_intervals
from unittest.mock import patch
import numpy as np

class FinalPre(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.pipeline=FinalPipeline();cls.manifest=verify_manifest()
    def test_hashes_congelados(self):self.assertEqual(verify_manifest()['model_id'],MODEL_ID)
    def test_origem_bytes(self):
        self.assertEqual(sha256(FINAL/'modelo.keras'),sha256(ROOT/self.manifest['source_paths']['model']))
        self.assertEqual(sha256(FINAL/'preprocessador.joblib'),sha256(ROOT/self.manifest['source_paths']['preprocessor']))
    def test_arquitetura_e_ordem(self):
        self.assertEqual(self.pipeline.model.input_shape[-1],299);self.assertEqual(self.pipeline.model.count_params(),19265)
        self.assertEqual([x.units for x in self.pipeline.model.layers],[64,1]);self.assertEqual(self.pipeline.preprocessor.features,FEATURES)
        self.assertEqual(self.manifest['transformed_features_order'],self.pipeline.preprocessor.names)
    def test_rotulos_e_threshold(self):
        self.assertEqual(self.manifest['labels'],{'0':'FURTO','1':'ROUBO'});self.assertEqual(self.manifest['threshold'],.5)
    def test_probabilidades_e_formato(self):
        for values in [(5,2,'VIA PÚBLICA','BELA VISTA'),(None,None,None,None),(1,0,'LOCAL NOVO','BAIRRO NOVO')]:
            r=self.pipeline.classificar(*values);p=r['probabilidade_roubo']
            self.assertTrue(np.isfinite(p));self.assertTrue(0<=p<=1);self.assertAlmostEqual(p+r['probabilidade_furto'],1)
            self.assertEqual(r['codigo_classe'],int(p>=.5));self.assertEqual(r['versao_modelo'],MODEL_ID)
            self.assertEqual(r['classe_estimada'],'ROUBO' if p>=.5 else 'FURTO');self.assertIsInstance(r['avisos'],list)
    def test_determinismo_inferencia(self):
        a=(5,2,'VIA PÚBLICA','BELA VISTA');self.assertEqual(self.pipeline.classificar(*a),self.pipeline.classificar(*a))
    def test_aliases_permitidos(self):
        a=self.pipeline.classificar(5,2,'VIA PUBLICA','BRAS');b=self.pipeline.classificar(5,2,' via pública ',' brás ')
        self.assertEqual(a,b)
    def test_desconhecidos_com_avisos(self):
        r=self.pipeline.classificar(5,2,'LOCAL INEXISTENTE','BAIRRO INEXISTENTE')
        self.assertEqual({w['codigo'] for w in r['avisos']},{'local_desconhecido','bairro_desconhecido'})
    def test_raro_com_aviso(self):
        p=self.pipeline.preprocessor;b=next(x for x in p.known['bairro'] if x not in p.frequent)
        r=self.pipeline.classificar(5,2,'VIA PÚBLICA',b)
        self.assertIn('bairro_raro',[w['codigo'] for w in r['avisos']])
    def test_ausente_sem_suporte_avisado(self):
        r=self.pipeline.classificar(None,None,None,None)
        self.assertEqual({w['campo'] for w in r['avisos'] if w['codigo']=='ausencia_sem_exemplos_treino'},{'mes','dia_semana'})
    def test_invalidos_rejeitados(self):
        for x in [('5',2,None,None),(5.0,2,None,None),(True,2,None,None),(13,2,None,None),(1,7,None,None),(0,0,None,None),(5,-1,None,None),(float('nan'),2,None,None),(5,2,123,None),(5,2,None,152)]:
            with self.assertRaises((ValueError,TypeError)):self.pipeline.classificar(*x)
        with self.assertRaises(TypeError):self.pipeline.classificar(5,2,None,None,alvo=1)
    def test_texto_bairro_invalido_nao_silencioso(self):
        r=self.pipeline.classificar(5,2,None,'152');self.assertIn('bairro_sem_nome',[w['codigo'] for w in r['avisos']])
    def test_sem_dependencia_dataset(self):
        original=Path.open
        def restricted(path,*args,**kwargs):
            if 'data' in path.parts:raise AssertionError('Inferencia leu dataset')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',restricted):self.assertIn(FinalPipeline().classificar(1,0,None,None)['codigo_classe'],[0,1])
    def test_preprocessador_nao_mutavel_na_transformacao(self):
        before=pickle.dumps(self.pipeline.preprocessor);self.pipeline.classificar(5,2,'NOVO','NOVO');self.assertEqual(before,pickle.dumps(self.pipeline.preprocessor))
    def test_calibracao_decidida_pelo_protocolo(self):
        d=read('decisao_calibracao.json');self.assertEqual(d['adopted'],all(d['checks'].values()))
        self.assertEqual((FINAL/'calibrador.joblib').exists(),d['adopted']);self.assertEqual(self.pipeline.calibrator is not None,d['adopted'])
        self.assertEqual(d['threshold'],.5);self.assertLess(d['decided_at'],self.manifest['frozen_at'])
    def test_2024_reproduzido(self):
        r=read('verificacao_previa_2024.json');self.assertEqual(r['n'],158895);self.assertLessEqual(r['max_abs_difference'],1e-7)
        self.assertAlmostEqual(r['metrics']['macro_f1'],.676902006111324,places=12)
    def test_preservacao_historico(self):self.assertGreater(preserve(),168)
    def test_manifesto_adulterado_rejeitado(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            for f in self.manifest['frozen_files']:shutil.copy2(FINAL/f,folder/f)
            for f in ['manifesto.json','manifesto.sha256']:shutil.copy2(FINAL/f,folder/f)
            with (folder/'config_final.json').open('a') as f:f.write(' ')
            with self.assertRaises(RuntimeError):verify_manifest(folder)

class FinalPost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved=np.load(OUT/'private/previsoes_2025.npz');cls.m=read('metricas_2025.json');cls.state=read('avaliacao_unica.json')
    def test_uma_avaliacao_apos_congelamento(self):
        self.assertEqual(self.state['status'],'completed');self.assertEqual(self.state['prediction_calls'],1)
        self.assertLess(self.state['frozen_at'],self.state['inference_started_at'])
        self.assertEqual(self.state['manifest_sha256'],sha256(FINAL/'manifesto.json'))
    def test_hashes_pos_avaliacao(self):
        verify_manifest();preserve()
        for path,h in self.state['result_hashes'].items():self.assertEqual(sha256(ROOT/path),h)
    def test_metricas_matriz_e_labels(self):
        m=metrics(self.saved['y_true'],self.saved['prob'])
        self.assertEqual(m,self.m);self.assertEqual(m['n'],156168)
        self.assertEqual(sum(sum(row) for row in m['confusion_matrix']),m['n'])
    def test_previsoes_finitas(self):
        p=self.saved['prob'];self.assertTrue(np.isfinite(p).all());self.assertTrue(((p>=0)&(p<=1)).all())
    def test_bootstrap_deterministico(self):
        ci=confidence_intervals(self.m)
        self.assertEqual(ci,read('intervalos_confianca_2025.json')['metrics'])
        for k,r in ci.items():self.assertLessEqual(r['lower'],r['point']);self.assertLessEqual(r['point'],r['upper'])
    def test_referencia_apenas_treino(self):
        r=read('referencia_majoritaria_2025.json');self.assertEqual(r['class_from_train'],0)
        self.assertFalse(r['test_labels_used_to_choose_class'])
        self.assertEqual(r['probability_from_train'],83703/190124)
    def test_pipeline_sem_ajustes_no_teste(self):
        p=read('verificacao_integridade.json');self.assertFalse(p['pipeline_adjusted_on_test']);self.assertFalse(p['training_on_2025'])
        self.assertTrue(p['test_inference_after_freeze']);self.assertEqual(p['alignment_mismatches'],0);self.assertEqual(p['unique_keys'],156168)
    def test_gate_idempotente_sem_reinferir(self):
        from final5.evaluate import evaluate_once
        before=sha256(OUT/'avaliacao_unica.json')
        with patch.object(FinalPipeline,'probabilities',side_effect=AssertionError('Nao repetir inferencia')):evaluate_once()
        self.assertEqual(before,sha256(OUT/'avaliacao_unica.json'))

if __name__=='__main__':unittest.main(verbosity=2)
