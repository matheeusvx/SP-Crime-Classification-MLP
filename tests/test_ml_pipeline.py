"""Testes novos: isolamento temporal, pre-processamento e modelo persistido."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ml.runtime import FEATURES,OUT,MODELS,sha256
import json
import pickle
import unittest
import joblib
import numpy as np
from ml.dataset import connection,validate,load_year,EXPECTED
from ml.preprocessing import Preprocessador,digest_keys,MISSING,RARE
from ml.evaluate import evaluate,predict_batched

class MLPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=connection();cls.validation=validate(cls.c)
        cls.tr,cls.y,cls.keys=load_year(cls.c,2023)
        cls.vr,cls.vy,cls.vkeys=load_year(cls.c,2024)
        cls.pre=joblib.load(MODELS/'preprocessador.joblib')
        cls.config=json.loads((MODELS/'config_modelo.json').read_text(encoding='utf-8'))
    def test_divisao_temporal(self):
        self.assertEqual(self.validation['counts'],EXPECTED)
        self.assertEqual(len(self.tr),190124);self.assertEqual(len(self.vr),158895)
    def test_chaves_disjuntas(self):
        a=set(self.keys);b=set(self.vkeys)
        t=set(x[0] for x in self.c.execute('SELECT chave_bo FROM meta WHERE ano_fato=2025').fetchall())
        self.assertFalse(a&b);self.assertFalse(a&t);self.assertFalse(b&t)
    def test_alinhamento_forte(self):
        self.assertTrue(all(self.validation['checks'].values()))
        # Perturbacao reversivel em uma VIEW em memoria deve impedir treinamento.
        c=connection()
        c.execute('''CREATE OR REPLACE VIEW meta AS SELECT * REPLACE (
          CASE WHEN indice_linha=0 THEN DATE '2020-01-01' ELSE data_fato END AS data_fato)
          FROM read_parquet('data/processed/metadados_modelagem.parquet')''')
        with self.assertRaisesRegex(ValueError,'Integridade/alinhamento'):validate(c)
        c.close()
    def test_entradas_sem_periodo_nem_proibidas(self):
        self.assertEqual(self.config['features'],FEATURES)
        self.assertEqual(FEATURES,['mes','dia_semana','tipo_local','bairro'])
        self.assertTrue(all(set(r)==set(FEATURES) for r in self.tr))
        self.assertFalse(any('periodo' in x or 'alvo' in x for x in self.pre.feature_names_))
        with self.assertRaises(ValueError):self.pre.transform([self.tr[0]|{'periodo_fato':'NOITE'}])
    def test_ajuste_so_treino(self):
        self.assertEqual(self.pre.fit_year_,2023);self.assertEqual(self.pre.fit_rows_,len(self.tr))
        self.assertEqual(self.pre.fit_keys_sha256_,digest_keys(self.keys))
        fresh=Preprocessador(self.pre.min_bairro_count).fit(self.tr,ano=2023,chaves=self.keys)
        self.assertEqual(fresh.feature_names_,self.pre.feature_names_)
        self.assertEqual(fresh.bairro_counts_,self.pre.bairro_counts_)
        self.assertEqual(fresh.aliases_,self.pre.aliases_)
        with self.assertRaises(ValueError):Preprocessador().fit(self.vr,ano=2024,chaves=self.vkeys)
    def test_transformacao_nao_reajusta(self):
        before=pickle.dumps(self.pre)
        self.pre.transform(self.vr[:2000])
        self.assertEqual(before,pickle.dumps(self.pre))
    def test_desconhecidos(self):
        record=dict(mes=5,dia_semana=2,tipo_local='LOCAL TOTALMENTE NOVO',bairro='BAIRRO TOTALMENTE NOVO')
        mat=self.pre.transform([record])
        self.assertEqual(mat.nnz,4)
        active=[self.pre.feature_names_[i] for i in mat.indices]
        self.assertIn('tipo_local_'+MISSING,active);self.assertIn('bairro_'+RARE,active)
        stats=self.pre.diagnostics([record])
        self.assertEqual(stats['bairro']['desconhecidos'],1);self.assertEqual(stats['tipo_local']['desconhecidos'],1)
    def test_ausentes_e_validacao_entradas(self):
        mat=self.pre.transform([dict(mes=None,dia_semana=None,tipo_local=None,bairro=None)])
        self.assertEqual(mat.nnz,4);self.assertEqual(mat.dtype,np.float32)
        self.assertTrue(np.isfinite(mat.data).all())
        with self.assertRaises(ValueError):self.pre.transform([dict(mes=13,dia_semana=2,tipo_local=None,bairro=None)])
        with self.assertRaises(ValueError):self.pre.transform([dict(mes=True,dia_semana=2,tipo_local=None,bairro=None)])
    def test_rotulos(self):
        self.assertEqual(set(self.y),{0,1});self.assertEqual(set(self.vy),{0,1})
        self.assertEqual(self.config['labels'],{'0':'FURTO','1':'ROUBO'})
        self.assertEqual(self.config['majority_class_train'],int(np.bincount(self.y).argmax()))
    def test_modelo_salvo_e_recarga(self):
        import tensorflow as tf
        model=tf.keras.models.load_model(MODELS/'mlp_baseline.keras',compile=False)
        self.assertEqual(model.input_shape[-1],len(self.pre.feature_names_))
        self.assertEqual([x.units for x in model.layers],[64,1])
        saved=np.load(OUT/'validacao_predicoes.npz')
        self.assertTrue(np.array_equal(saved['y_true'],self.vy))
        np.testing.assert_allclose(predict_batched(model,self.pre.transform(self.vr[:512])),saved['prob_roubo'][:512],atol=1e-7,rtol=0)
    def test_inferencia_python(self):
        from ml.inference import ClassificadorOcorrencias
        model=ClassificadorOcorrencias()
        for args in [(5,2,'Via pública','Bela Vista'),(1,0,None,None),(7,6,'LOCAL NOVO','BAIRRO NOVO')]:
            r=model.classificar(*args)
            self.assertIn(r['classe'],['FURTO','ROUBO'])
            self.assertAlmostEqual(r['probabilidade_furto']+r['probabilidade_roubo'],1,places=7)
            self.assertTrue(0<=r['probabilidade_roubo']<=1)
            self.assertFalse(r['probabilidades_calibradas'])
    def test_teste_final_bloqueado(self):
        with self.assertRaises(ValueError):load_year(self.c,2025)
        with self.assertRaises(ValueError):evaluate([],[],year=2025,name='proibido')
        access=json.loads((OUT/'acesso_dados.json').read_text(encoding='utf-8'))
        self.assertEqual(access['test_prediction_count'],0);self.assertEqual(access['test_transformed_count'],0)
        self.assertEqual(access['prediction_years'],[2023,2024]);self.assertEqual(access['fit_preprocessor_years'],[2023])
        metrics=json.loads((OUT/'metricas_baseline.json').read_text(encoding='utf-8'))
        self.assertNotIn(2025,[m['ano'] for m in metrics])
        self.assertEqual(access['architectures_trained'],1);self.assertFalse(access['hyperparameter_search'])
    def test_preservacao_etapa1(self):
        manifest=json.loads((OUT/'etapa1_preservacao.json').read_text(encoding='utf-8'))
        from maintenance56.integrity import verify_history
        self.assertGreater(verify_history(manifest),0)
    def test_hashes_artefatos(self):
        hashes=json.loads((OUT/'artefatos_sha256.json').read_text(encoding='utf-8'))
        for name,checksum in hashes.items():self.assertEqual(sha256(MODELS/name),checksum)
    def test_early_stopping_e_config(self):
        history=json.loads((OUT/'historico_mlp.json').read_text(encoding='utf-8'))
        self.assertLessEqual(len(history),30);self.assertGreater(len(history),0)
        self.assertEqual(self.config['best_epoch'],1+int(np.argmin([r['val_loss'] for r in history])))
        self.assertTrue(all(np.isfinite([r['loss'],r['val_loss'],r['accuracy'],r['val_accuracy']]).all() for r in history))
        self.assertTrue(self.config['early_stopping']['restore_best_weights'])

if __name__=='__main__':unittest.main(verbosity=2)
