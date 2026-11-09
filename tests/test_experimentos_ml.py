"""Etapa 4: desenho experimental, particionamento, artefatos e comparacoes."""
import sys,json,csv,unittest,pickle,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from experiments4.common import OUT,MODELS,FEATURES,read,preserve,data,sha256
from experiments4.preprocessing import ExperimentalPreprocessor
from experiments4.engine import score,subset
from ml.preprocessing import digest_keys
import numpy as np
import joblib

class Experimentos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs=[json.loads(p.read_text(encoding='utf-8')) for p in (OUT/'runs').glob('*.json')]
        cls.records,cls.y,cls.keys=data(2023);cls.val,cls.vy,cls.vkeys=data(2024)
        cls.internal=[i for i,r in enumerate(cls.records) if r['mes']<=9];cls.holdout=[i for i,r in enumerate(cls.records) if r['mes']>=10]
    def test_matriz_previa_integridade(self):
        plan=read('matriz_planejada.json')
        self.assertTrue(plan['no_test_2025']);self.assertEqual(plan['architecture_units'],[[32],[64],[64,32]])
        checksum=sha256(OUT/'matriz_planejada.json')
        for r in self.runs:self.assertEqual(r['plan_hash'],checksum)
    def test_divisao_temporal(self):
        self.assertEqual(len(self.internal),144697);self.assertEqual(len(self.holdout),45427)
        a={self.keys[i] for i in self.internal};b={self.keys[i] for i in self.holdout}
        self.assertFalse(a&b);self.assertEqual(a|b,set(self.keys));self.assertFalse(set(self.keys)&set(self.vkeys))
    def test_sem_2025(self):
        with self.assertRaises(ValueError):data(2025)
        for r in self.runs:
            self.assertEqual(r['train_years'],[2023]);self.assertNotIn(2025,r['validation_years'])
        self.assertEqual(read('acesso_dados.json')['test_2025_predictions'],0)
    def test_fit_apenas_treino_correspondente(self):
        for r in self.runs:
            pre=joblib.load(ROOT/r['preprocessor_path'])
            keys=[self.keys[i] for i in self.internal] if r['scope']=='internal' else self.keys
            self.assertEqual(pre.fit_keys_hash,digest_keys(keys));self.assertEqual(pre.rows,len(keys))
            self.assertEqual(pre.months,list(range(1,10)) if r['scope']=='internal' else list(range(1,13)))
            self.assertEqual(pre.scope,'interno_2023_JanSet' if r['scope']=='internal' else 'completo_2023')
    def test_esquema_sem_proibidos(self):
        for r in self.runs:
            self.assertTrue(set(r['config']['features'])<=set(FEATURES))
            self.assertNotIn('periodo_fato',r['config']['features'])
            pre=joblib.load(ROOT/r['preprocessor_path'])
            self.assertEqual(pre.features,r['config']['features'])
            record={f:self.records[0][f] for f in pre.features}
            with self.assertRaises(ValueError):pre.transform([record|{'alvo':0}])
    def test_meses_fora_treino_rejeitados_no_fit(self):
        p=ExperimentalPreprocessor(['dia_semana'],50)
        with self.assertRaises(ValueError):p.fit([{'dia_semana':1}],scope='interno_2023_JanSet',keys=['k'],months=[10])
        with self.assertRaises(ValueError):p.fit([{'dia_semana':1}],scope='2025',keys=['k'],months=[1])
    def test_sem_refit_transformacao(self):
        r=next(r for r in self.runs if r['scope']=='full');pre=joblib.load(ROOT/r['preprocessor_path']);before=pickle.dumps(pre)
        pre.transform(subset(self.val[:100],pre.features));self.assertEqual(before,pickle.dumps(pre))
    def test_a5_sem_fusao_outros_e_ausente(self):
        r=read('runs/A5_internal_s42.json');pre=joblib.load(ROOT/r['preprocessor_path'])
        common={'mes':5,'dia_semana':2,'bairro':'BELA VISTA'}
        a=pre.transform([common|{'tipo_local':'VIA PUBLICA'}]);b=pre.transform([common|{'tipo_local':'VIA PÚBLICA'}])
        self.assertEqual((a!=b).nnz,0)
        self.assertGreater((pre.transform([common|{'tipo_local':'OUTROS'}])!=pre.transform([common|{'tipo_local':None}])).nnz,0)
        self.assertEqual(r['reused_from'],'A0_internal_s42')
    def test_desconhecidos_e_ausentes(self):
        r=next(r for r in self.runs if r['id']=='B64' and r['scope']=='full');pre=joblib.load(ROOT/r['preprocessor_path'])
        a={f:None if f in ['bairro','tipo_local'] else 5 if f=='mes' else 2 for f in pre.features}
        b=a|{f:'NOME NUNCA OBSERVADO' for f in ['bairro','tipo_local'] if f in pre.features}
        for values in [a,b]:
            x=pre.transform([values]);self.assertEqual(x.nnz,len(pre.features));self.assertTrue(np.isfinite(x.data).all())
    def test_tres_arquiteturas_comparaveis(self):
        rs=[next(r for r in self.runs if r['id']==id and r['scope']=='full' and r['seed']==42) for id in ['B32','B64','B64_32']]
        self.assertEqual([r['config']['units'] for r in rs],[[32],[64],[64,32]])
        for r in rs:
            self.assertEqual(r['config']['features'],rs[0]['config']['features']);self.assertEqual(r['input_dimension'],rs[0]['input_dimension'])
            self.assertEqual(r['config']['lr'],.001);self.assertEqual(r['batch_size'],256);self.assertEqual(r['threshold'],.5)
    def test_epocas_congeladas_sem_2024_early_stopping(self):
        agenda={r['id']:r for r in read('agenda_reajuste_congelada.json')['agenda']}
        for r in self.runs:
            if r['scope']=='full':
                self.assertEqual(r['epochs_ran'],agenda[r['id']]['fixed_epochs'])
                self.assertIsNone(r['early_stopping_validation_year']);self.assertNotIn('val_loss',r['history'])
                self.assertEqual(r['fixed_epoch_budget'],r['epochs_ran'])
    def test_estabilidade_sementes_mesma_config(self):
        for candidate in read('agenda_reajuste_congelada.json')['candidates']:
            for scope in ['internal','full']:
                rs=[read(f'runs/{candidate["id"]}_{scope}_s{seed}.json') for seed in [42,7,123]]
                self.assertEqual(len({json.dumps(r['config'],sort_keys=True) for r in rs}),1)
                self.assertEqual([r['batch_order_seed'] for r in rs],[42,42,42])
    def test_metricas_recalculadas(self):
        from sklearn.metrics import f1_score,confusion_matrix
        for r in self.runs:
            npz=np.load(ROOT/r['prediction_path']);y=npz['y_true'];p=npz['prob_roubo'];m=r['validation_metrics']
            self.assertEqual(set(np.unique(y)),{0,1});self.assertEqual(len(y),r['validation_n'])
            self.assertAlmostEqual(f1_score(y,p>=.5,average='macro'),m['macro_f1'],places=12)
            self.assertEqual(confusion_matrix(y,p>=.5,labels=[0,1]).ravel().tolist(),[m[k] for k in ['tn','fp','fn','tp']])
            self.assertTrue(np.isfinite(p).all());self.assertTrue(((p>=0)&(p<=1)).all())
    def test_hashes_todos_artefatos(self):
        for r in self.runs:
            for name,h in r['artifact_hashes'].items():self.assertEqual(sha256(ROOT/name),h)
    def test_carregamento_e_inferencia(self):
        from experiments4.inference import ExperimentalPredictor
        for id in ['B32','B64','B64_32']:
            p=OUT/f'runs/{id}_full_s42.json';predictor=ExperimentalPredictor(p)
            record={f:self.val[0][f] for f in predictor.pre.features};r=predictor.predict(**record)
            self.assertAlmostEqual(r['probabilidade_roubo']+r['probabilidade_furto'],1)
            self.assertEqual(r['codigo'],int(r['probabilidade_roubo']>=.5));self.assertFalse(r['calibrada'])
    def test_baseline_preservado(self):
        from maintenance56.integrity import verify_history
        self.assertGreater(verify_history(read('preservacao.json')),100)
    def test_tabelas_integras(self):
        for name in ['resultados_experimentos','comparacao_arquiteturas','comparacao_atributos','comparacao_regularizacao']:
            with (OUT/(name+'.csv')).open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            self.assertGreater(len(rows),0)
        with (OUT/'resultados_experimentos.csv').open(encoding='utf-8-sig') as f:table=list(csv.DictReader(f))
        self.assertEqual(len(table),len(self.runs))
        self.assertEqual({r['run_id'] for r in table},{r['run_id'] for r in self.runs})

if __name__=='__main__':unittest.main(verbosity=2)
