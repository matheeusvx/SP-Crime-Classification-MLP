"""Uma unica arquitetura inicial; 2023 treino, 2024 validacao, 2025 isolado."""
from ml.runtime import *
import argparse
import collections
import csv
import importlib.metadata
import json
import time
import traceback
import platform
import numpy as np
import joblib
import psutil
from ml.dataset import connection,validate,load_year
from ml.preprocessing import Preprocessador,digest_keys
from ml.evaluate import predict_batched,evaluate

def train(min_bairro_count=50):
    OUT.mkdir(parents=True,exist_ok=True);MODELS.mkdir(exist_ok=True)
    start=time.perf_counter();tf=configure_tf(42)
    # O snapshot inclui apenas arquivos anteriores a Etapa 2.
    snapshot=stage1_snapshot();json_write(OUT/'etapa1_preservacao.json',snapshot)
    c=connection();valid=validate(c,True)
    records,y,keys=load_year(c,2023);vr,vy,vkeys=load_year(c,2024)
    if set(keys)&set(vkeys):raise ValueError('Sobreposicao entre treino e validacao')
    pre=Preprocessador(min_bairro_count).fit(records,ano=2023,chaves=keys)
    X=pre.transform(records);V=pre.transform(vr)
    for name,m in [('treino',X),('validacao',V)]:
        print(f'{name}: {m.shape}, CSR {(m.data.nbytes+m.indices.nbytes+m.indptr.nbytes)/1024**2:.2f} MiB',flush=True)
    dimension=X.shape[1]
    # So um lote e densificado por vez, tanto no treino como na inferencia.
    class Batches(tf.keras.utils.PyDataset):
        def __init__(self,x,y,shuffle):
            super().__init__(workers=1,use_multiprocessing=False,max_queue_size=2)
            self.x=x;self.y=y;self.shuffle=shuffle;self.indices=np.arange(len(y));self.rng=np.random.default_rng(42)
            if shuffle:self.rng.shuffle(self.indices)
        def __len__(self):return (len(self.y)+255)//256
        def __getitem__(self,index):
            ids=self.indices[index*256:(index+1)*256]
            return self.x[ids].toarray(),self.y[ids].astype(np.float32).reshape(-1,1)
        def on_epoch_end(self):
            if self.shuffle:self.rng.shuffle(self.indices)
    class LogEpoch(tf.keras.callbacks.Callback):
        def on_epoch_begin(self,epoch,logs=None):self.start=time.perf_counter()
        def on_epoch_end(self,epoch,logs=None):
            row={'epoca':epoch+1,**{k:float(v) for k,v in logs.items()},'seconds':time.perf_counter()-self.start,
                 'rss_mb':psutil.Process().memory_info().rss/1024**2}
            epochs.append(row);json_write(OUT/'historico_mlp.json',epochs)
            print(f"epoca {epoch+1:02d} loss={row['loss']:.5f} val_loss={row['val_loss']:.5f} accuracy={row['accuracy']:.4f} val_accuracy={row['val_accuracy']:.4f} {row['seconds']:.1f}s",flush=True)
    model=tf.keras.Sequential([tf.keras.layers.Input(shape=(dimension,),name='atributos_one_hot'),
      tf.keras.layers.Dense(64,activation='relu',name='oculta_relu'),tf.keras.layers.Dense(1,activation='sigmoid',name='probabilidade_roubo')])
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=.001),loss='binary_crossentropy',metrics=[tf.keras.metrics.BinaryAccuracy(name='accuracy')])
    epochs=[];early=tf.keras.callbacks.EarlyStopping(monitor='val_loss',mode='min',patience=5,min_delta=0,restore_best_weights=True)
    training_start=time.perf_counter()
    model.fit(Batches(X,y,True),validation_data=Batches(V,vy,False),epochs=30,
              callbacks=[early,LogEpoch()],shuffle=False,verbose=0)
    training_seconds=time.perf_counter()-training_start
    train_prob=predict_batched(model,X);val_prob=predict_batched(model,V)
    majority=int(np.bincount(y,minlength=2).argmax())
    results=[evaluate(y,train_prob,year=2023,name='MLP'),evaluate(vy,val_prob,year=2024,name='MLP'),
             evaluate(vy,np.full(len(vy),float(majority)),year=2024,name='Majoritario')]
    model.save(MODELS/'mlp_baseline.keras');joblib.dump(pre,MODELS/'preprocessador.joblib')
    model_json=model.to_json();(MODELS/'arquitetura_mlp.json').write_text(model_json,encoding='utf-8')
    versions={m:importlib.metadata.version(m) for m in ['tensorflow','keras','scikit-learn','joblib','numpy','scipy','pyarrow','duckdb','matplotlib']}
    config={'features':FEATURES,'types':{'mes':'inteiro 1..12 ou None','dia_semana':'inteiro 0..6 (segunda=0) ou None','tipo_local':'texto ou None','bairro':'texto ou None'},
      'labels':{'0':'FURTO','1':'ROUBO'},'threshold':.5,'input_dimension':dimension,'hidden_units':64,'activation':'relu','output':'sigmoid',
      'trainable_parameters':int(model.count_params()),'loss':'binary_crossentropy','optimizer':'Adam','learning_rate':.001,
      'batch_size':256,'max_epochs':30,'early_stopping':{'monitor':'val_loss','patience':5,'min_delta':0,'restore_best_weights':True},
      'seed':42,'min_bairro_count':min_bairro_count,'fit_year':2023,'validation_year':2024,'test_year':2025,
      'train_rows':len(y),'validation_rows':len(vy),'test_rows_isolated':valid['counts'][2025],
      'epochs_ran':len(epochs),'best_epoch':int(np.argmin([e['val_loss'] for e in epochs]))+1,
      'stop_reason':'early_stopping_val_loss' if early.stopped_epoch>0 else 'maximo_30_epocas',
      'training_seconds':training_seconds,'pipeline_seconds_before_save_checks':time.perf_counter()-start,
      'train_keys_sha256':digest_keys(keys),'validation_keys_sha256':digest_keys(vkeys),
      'dependencies':versions,'python':sys.version,'platform':platform.platform(),
      'cpu_logical':psutil.cpu_count(),'ram_gib':psutil.virtual_memory().total/1024**3,
      'tensorflow_devices':[{'name':d.name,'type':d.device_type} for d in tf.config.list_physical_devices()],
      'tf_intra_threads':4,'tf_inter_threads':1,'deterministic_ops':True,'oneDNN':os.environ.get('TF_ENABLE_ONEDNN_OPTS'),
      'probabilidades_calibradas':False,'majority_class_train':majority,
      'etapa1_sha256':snapshot}
    json_write(MODELS/'config_modelo.json',config)
    reloaded=tf.keras.models.load_model(MODELS/'mlp_baseline.keras',compile=False)
    reloaded_pre=joblib.load(MODELS/'preprocessador.joblib')
    # Conferencia completa de validacao apos recarregamento, ainda sem acessar 2025.
    loaded_prob=predict_batched(reloaded,reloaded_pre.transform(vr))
    delta=float(np.max(np.abs(val_prob-loaded_prob)))
    if not np.allclose(val_prob,loaded_prob,rtol=0,atol=1e-7):raise ValueError('Predicoes divergentes apos salvar/recarregar')
    json_write(OUT/'consistencia_recarga.json',{'validation_rows':len(vy),'max_abs_difference':delta,'passed':True})
    json_write(OUT/'metricas_baseline.json',results)
    json_write(OUT/'preprocessamento.json',{'treino':pre.train_stats_,'validacao':pre.diagnostics(vr)})
    json_write(OUT/'acesso_dados.json',{'training_years':[2023],'fit_preprocessor_years':[2023],
      'prediction_years':[2023,2024],'evaluation_years':[2023,2024],'test_year':2025,'test_prediction_count':0,
      'test_transformed_count':0,'test_usage':'apenas verificacoes estruturais de integridade',
      'features':FEATURES,'threshold_fixed':.5,'hyperparameter_search':False,'architectures_trained':1})
    np.savez_compressed(OUT/'validacao_predicoes.npz',y_true=vy,prob_roubo=val_prob)
    with (OUT/'historico_mlp.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(epochs[0]));w.writeheader();w.writerows(epochs)
    json_write(OUT/'artefatos_sha256.json',{p.name:sha256(p) for p in MODELS.iterdir() if p.is_file()})
    print(json.dumps({'config':{k:v for k,v in config.items() if k!='etapa1_sha256'},'metricas':results},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--min-bairro-count',type=int,default=50);args=p.parse_args()
    try:train(args.min_bairro_count)
    except Exception:
        OUT.mkdir(parents=True,exist_ok=True)
        with (OUT/'falhas_execucao.log').open('a',encoding='utf-8') as f:traceback.print_exc(file=f)
        raise
