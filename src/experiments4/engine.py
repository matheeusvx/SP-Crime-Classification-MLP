"""Treinos internos e reajustes fixos; execucoes rastreaveis e cache validado."""
from experiments4.common import *
from experiments4.preprocessing import ExperimentalPreprocessor
from ml.runtime import configure_tf
from ml.preprocessing import MISSING,digest_keys
from ml.evaluate import predict_batched
from diagnostics.common import metrics
import numpy as np
import joblib,time,hashlib,datetime,traceback,pickle,shutil,sys,platform,importlib.metadata
from sklearn.metrics import brier_score_loss,log_loss

CONFIG_KEYS=['features','min_count','local_alias','units','dropout','l2','lr']
def canonical(spec):return {k:spec[k] for k in CONFIG_KEYS}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def subset(records,features):return [{f:r[f] for f in features} for r in records]

def score(y,p):
    r=metrics(y,p);tn,fp,fn,tp=[r[k] for k in ['tn','fp','fn','tp']]
    div=lambda a,b:float(a/b) if b else 0.
    pred=p>=.5;confidence=np.maximum(p,1-p);err=pred!=y
    r.update(precision_furto=div(tn,tn+fn),recall_furto=div(tn,tn+fp),f1_furto=div(2*tn,2*tn+fp+fn),
      fpr=div(fp,tn+fp),fnr=div(fn,tp+fn),brier=float(brier_score_loss(y,p)),log_loss=float(log_loss(y,p,labels=[0,1])),
      high_conf_errors=int(sum(err&(confidence>=.9))),high_conf_fn=int(sum(err&(confidence>=.9)&(y==1))))
    ids=np.minimum((p*10).astype(int),9);r['ece10']=float(sum(sum(ids==i)/len(y)*abs(np.mean(p[ids==i])-np.mean(y[ids==i])) for i in range(10) if np.any(ids==i)))
    return r

class Engine:
    def __init__(self):
        preserve();self.tf=configure_tf(42);self.records,self.y,self.keys=data(2023)
        environment={'python':sys.version,'platform':platform.platform(),'dependencies':{m:importlib.metadata.version(m) for m in ['tensorflow','keras','scikit-learn','numpy','scipy','joblib','pyarrow','duckdb']},
          'tensorflow_devices':[{'name':x.name,'type':x.device_type} for x in self.tf.config.list_physical_devices()],
          'threads_intra':4,'threads_inter':1,'deterministic_ops':True,'batch_order_seed':42,'oneDNN':False}
        json_write(OUT/'ambiente.json',environment)
        self.months=np.asarray([r['mes'] for r in self.records]);self.i=np.flatnonzero(self.months<=9);self.v=np.flatnonzero(self.months>=10)
        assert not(set(self.keys[i] for i in self.i)&set(self.keys[i] for i in self.v))
        self.external=None;self.pre_cache={};(OUT/'runs').mkdir(parents=True,exist_ok=True)
        splits=[]
        for name,ids in [('treino_interno',self.i),('validacao_interna',self.v)]:
            splits.append({'particao':name,'n':len(ids),'mes_min':int(self.months[ids].min()),'mes_max':int(self.months[ids].max()),'furtos':int(sum(self.y[ids]==0)),'roubos':int(sum(self.y[ids]==1)),'keys_sha256':digest_keys([self.keys[i] for i in ids])})
        json_write(OUT/'divisao_interna.json',splits)
        self.data_hashes={f:sha256(ROOT/f'data/processed/{f}.parquet') for f in ['base_modelagem','metadados_modelagem','ocorrencias_elegiveis']}
    def arrays(self,scope):
        if scope=='internal':return ([self.records[i] for i in self.i],self.y[self.i],[self.keys[i] for i in self.i],[self.records[i] for i in self.v],self.y[self.v],[self.keys[i] for i in self.v])
        if scope!='full':raise ValueError('Escopo invalido: 2025 nao permitido')
        if self.external is None:self.external=data(2024)
        vr,vy,vkeys=self.external
        assert not set(self.keys)&set(vkeys)
        return self.records,self.y,self.keys,vr,vy,vkeys
    def preprocessing(self,spec,scope):
        key=digest({k:spec[k] for k in ['features','min_count','local_alias']}|{'scope':scope})
        if key in self.pre_cache:return self.pre_cache[key]
        tr,y,keys,vr,vy,vkeys=self.arrays(scope)
        pre=ExperimentalPreprocessor(spec['features'],spec['min_count'],spec['local_alias']).fit(subset(tr,spec['features']),scope='interno_2023_JanSet' if scope=='internal' else 'completo_2023',keys=keys,months=[r['mes'] for r in tr])
        X=pre.transform(subset(tr,spec['features']));V=pre.transform(subset(vr,spec['features']))
        self.pre_cache[key]=(pre,X,V);return pre,X,V
    def groups(self,pre,vr,y,p,scope):
        tr,*_=self.arrays(scope)
        # Grupos de referencia sempre definidos por threshold50 e somente pelo treino correspondente.
        refspec={'features':FEATURES,'min_count':50,'local_alias':False}
        reference=self.preprocessing(refspec,scope)[0]
        def classify(proc,r):
            if 'bairro' not in proc.features:return 'nao_usado'
            b=proc._raw({f:r[f] for f in proc.features})[proc.features.index('bairro')]
            return 'ausente' if b==MISSING else 'frequente' if b in proc.frequent else 'raro_conhecido' if b in proc.known['bairro'] else 'desconhecido'
        definitions={'bairro_referencia_50':[classify(reference,r) for r in vr],
          'bairro_proprio':[classify(pre,r) for r in vr],
          'presenca_local':['ausente' if r['tipo_local'] is None else 'preenchido' for r in vr],
          'tipo_local':['(AUSENTE)' if r['tipo_local'] is None else r['tipo_local'] for r in vr],
          'mes':[str(r['mes']) for r in vr]}
        out=[]
        for f,values in definitions.items():
            values=np.asarray(values,dtype=object)
            for category in sorted(set(values)):
                mask=values==category;m=score(y[mask],p[mask])
                out.append({'grupo':f,'categoria':category,**m,'destacar':m['n']>=200 and min(m['furtos'],m['roubos'])>=30})
        return out
    def run(self,id,spec,scope='internal',seed=42,epochs=None,reuse=None):
        path=OUT/f'runs/{id}_{scope}_s{seed}.json';signature=digest({'config':canonical(spec),'scope':scope,'seed':seed,'epochs':epochs,'data':self.data_hashes,'plan':PLAN_VERSION})
        if path.exists():
            r=json.loads(path.read_text(encoding='utf-8'))
            if r['signature']!=signature:raise RuntimeError('Cache com configuracao diferente: '+str(path))
            if all((ROOT/p).exists() and sha256(ROOT/p)==h for p,h in r['artifact_hashes'].items()):print('Cache valido:',r['run_id'],flush=True);return r
            raise RuntimeError('Artefato em cache invalido: '+str(path))
        for old in (OUT/'runs').glob('*.json'):
            r=json.loads(old.read_text(encoding='utf-8'))
            if r.get('signature')==signature:
                if not all(sha256(ROOT/p)==h for p,h in r['artifact_hashes'].items()):raise RuntimeError('Artefato de reutilizacao alterado')
                r=r|{'id':id,'run_id':path.stem,'hypothesis':spec['hypothesis'],'factor':spec['factor'],'reused_from':r['run_id'],'training_seconds':0.}
                json_write(path,r);return r
        start=time.perf_counter();tr,y,keys,vr,vy,vkeys=self.arrays(scope);pre,X,V=self.preprocessing(spec,scope)
        before=pickle.dumps(pre);dest=MODELS/path.stem;dest.mkdir(parents=True,exist_ok=True)
        try:
            if reuse:
                source=json.loads((OUT/f'runs/{reuse}.json').read_text(encoding='utf-8'))
                sourcepre=joblib.load(ROOT/source['preprocessor_path'])
                SX=sourcepre.transform(subset(tr,sourcepre.features));SV=sourcepre.transform(subset(vr,sourcepre.features))
                if X.shape!=SX.shape or (X!=SX).nnz or (V!=SV).nnz:raise ValueError('A5 nao equivalente: exige revisao, nao adicionar treino automaticamente')
                model=self.tf.keras.models.load_model(ROOT/source['model_path'],compile=False);history=source['history'];train_seconds=0.;best_epoch=source['best_epoch'];reused_from=source['run_id']
            else:
                tf=self.tf;tf.keras.backend.clear_session();tf.keras.utils.set_random_seed(seed)
                layers=[tf.keras.layers.Input(shape=(X.shape[1],))]
                for units in spec['units']:
                    layers.append(tf.keras.layers.Dense(units,activation='relu',kernel_regularizer=tf.keras.regularizers.L2(spec['l2']) if spec['l2'] else None))
                    if spec['dropout']:layers.append(tf.keras.layers.Dropout(spec['dropout']))
                layers.append(tf.keras.layers.Dense(1,activation='sigmoid'));model=tf.keras.Sequential(layers)
                model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=spec['lr']),loss='binary_crossentropy',metrics=[tf.keras.metrics.BinaryAccuracy(name='accuracy')])
                class Batches(tf.keras.utils.PyDataset):
                    def __init__(self,x,labels,shuffle):
                        super().__init__(workers=1,use_multiprocessing=False,max_queue_size=2)
                        self.x=x;self.y=labels;self.shuffle=shuffle;self.ids=np.arange(len(labels));self.rng=np.random.default_rng(42)
                        if shuffle:self.rng.shuffle(self.ids)
                    def __len__(self):return (len(self.ids)+255)//256
                    def __getitem__(self,i):
                        ids=self.ids[i*256:(i+1)*256];return self.x[ids].toarray(),self.y[ids].astype(np.float32).reshape(-1,1)
                    def on_epoch_end(self):
                        if self.shuffle:self.rng.shuffle(self.ids)
                class Progress(tf.keras.callbacks.Callback):
                    def on_epoch_end(self,epoch,logs=None):
                        if epoch==0 or (epoch+1)%5==0:print(f'{path.stem}: epoca {epoch+1}, loss {logs["loss"]:.5f}'+(f', val_loss {logs["val_loss"]:.5f}' if 'val_loss' in logs else ''),flush=True)
                early=tf.keras.callbacks.EarlyStopping(monitor='val_loss',mode='min',patience=5,restore_best_weights=True)
                fit_start=time.perf_counter();h=model.fit(Batches(X,y,True),validation_data=Batches(V,vy,False) if scope=='internal' else None,epochs=30 if scope=='internal' else epochs,
                    callbacks=[early,Progress()] if scope=='internal' else [Progress()],shuffle=False,verbose=0)
                train_seconds=time.perf_counter()-fit_start;history={k:[float(v) for v in values] for k,values in h.history.items()}
                best_epoch=int(np.argmin(history['val_loss']))+1 if scope=='internal' else epochs;reused_from=None
            pt=predict_batched(model,X);p=predict_batched(model,V)
            tm=score(y,pt);vm=score(vy,p)
            model.save(dest/'modelo.keras');joblib.dump(pre,dest/'preprocessador.joblib')
            reloaded=self.tf.keras.models.load_model(dest/'modelo.keras',compile=False)
            recarga=predict_batched(reloaded,V[:512]);assert np.allclose(recarga,p[:512],atol=1e-7,rtol=0)
            np.savez_compressed(dest/'predicoes_validacao.npz',y_true=vy,prob_roubo=p)
            assert before==pickle.dumps(pre)
            r={'id':id,'run_id':path.stem,'scope':scope,'seed':seed,'signature':signature,'config':canonical(spec),
              'hypothesis':spec['hypothesis'],'factor':spec['factor'],'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'train_n':len(y),'validation_n':len(vy),'train_keys_hash':digest_keys(keys),'validation_keys_hash':digest_keys(vkeys),
              'train_years':[2023],'validation_years':[2023] if scope=='internal' else [2024],'environment_path':'reports/etapa4/ambiente.json',
              'input_dimension':X.shape[1],'parameters':int(model.count_params()),'epochs_ran':len(history['loss']),'best_epoch':best_epoch,
              'fixed_epoch_budget':epochs,'early_stopping_validation_year':2023 if scope=='internal' else None,
              'training_seconds':train_seconds,'total_seconds':time.perf_counter()-start,'threshold':.5,'batch_size':256,'batch_order_seed':42,
              'train_metrics':tm,'validation_metrics':vm,'history':history,'preprocess_train':pre.stats,'preprocess_validation':pre.describe(subset(vr,pre.features)),
              'groups':self.groups(pre,vr,vy,p,scope),'data_hashes':self.data_hashes,'plan_hash':sha256(OUT/'matriz_planejada.json'),
              'reused_from':reused_from,'preprocessor_path':(dest/'preprocessador.joblib').relative_to(ROOT).as_posix(),
              'model_path':(dest/'modelo.keras').relative_to(ROOT).as_posix(),'prediction_path':(dest/'predicoes_validacao.npz').relative_to(ROOT).as_posix(),
              'status':'completed','reload_max_abs_diff':float(np.max(np.abs(recarga-p[:512])))}
            json_write(dest/'config.json',{k:v for k,v in r.items() if k not in ['groups','history']})
            r['artifact_hashes']={p.relative_to(ROOT).as_posix():sha256(p) for p in dest.iterdir() if p.is_file()}
            json_write(path,r)
            with (OUT/'eventos.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'run':path.stem,'status':'completed','macro_f1':vm['macro_f1']})+'\n')
            print(f"{path.stem} concluido: Macro F1={vm['macro_f1']:.5f}, recall={vm['recall_roubo']:.5f}, {train_seconds:.1f}s",flush=True)
            return r
        except Exception:
            with (OUT/'falhas.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'run':path.stem,'config':canonical(spec),'status':'failed','error':traceback.format_exc()})+'\n')
            raise
