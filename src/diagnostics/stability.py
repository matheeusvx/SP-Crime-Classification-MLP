"""Tres repeticoes diagnosticas: controle 42 e sementes 7 e 123, sem selecao."""
from diagnostics.common import *
from ml.runtime import configure_tf
from ml.dataset import connection,load_year
from ml.evaluate import predict_batched
import argparse,time,joblib

def run(seed):
    preserve();tf=configure_tf(seed);c=connection()
    tr,y,_=load_year(c,2023);vr,vy,_=load_year(c,2024)
    pre=joblib.load(MODELS/'preprocessador.joblib');X=pre.transform(tr);V=pre.transform(vr)
    class Batches(tf.keras.utils.PyDataset):
        def __init__(self,x,y,shuffle):
            super().__init__(workers=1,use_multiprocessing=False,max_queue_size=2)
            self.x=x;self.y=y;self.shuffle=shuffle;self.indices=np.arange(len(y));self.rng=np.random.default_rng(42)
            if shuffle:self.rng.shuffle(self.indices)
        def __len__(self):return (len(self.y)+255)//256
        def __getitem__(self,index):
            ids=self.indices[index*256:(index+1)*256];return self.x[ids].toarray(),self.y[ids].astype(np.float32).reshape(-1,1)
        def on_epoch_end(self):
            if self.shuffle:self.rng.shuffle(self.indices)
    model=tf.keras.Sequential([tf.keras.layers.Input(shape=(X.shape[1],),name='atributos_one_hot'),tf.keras.layers.Dense(64,activation='relu',name='oculta_relu'),tf.keras.layers.Dense(1,activation='sigmoid',name='probabilidade_roubo')])
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=.001),loss='binary_crossentropy',metrics=[tf.keras.metrics.BinaryAccuracy(name='accuracy')])
    early=tf.keras.callbacks.EarlyStopping(monitor='val_loss',mode='min',patience=5,min_delta=0,restore_best_weights=True)
    class Progress(tf.keras.callbacks.Callback):
        def on_epoch_end(self,epoch,logs=None):print(f'semente {seed}, epoca {epoch+1}, val_loss {logs["val_loss"]:.6f}',flush=True)
    start=time.perf_counter();h=model.fit(Batches(X,y,True),validation_data=Batches(V,vy,False),epochs=30,callbacks=[early,Progress()],shuffle=False,verbose=0).history
    duration=time.perf_counter()-start;p=predict_batched(model,V)
    result={'seed':seed,'batch_order_seed':42,'epochs':len(h['loss']),'best_epoch':int(np.argmin(h['val_loss']))+1,'seconds':duration,**metrics(vy,p),
       'config':{'units':[64,1],'activations':['relu','sigmoid'],'input':X.shape[1],'learning_rate':.001,'batch_size':256,'max_epochs':30,'patience':5,'restore_best_weights':True,'threshold':.5,'preprocessor_sha256':sha256(MODELS/'preprocessador.joblib'),'train_year':2023,'validation_year':2024},'history':h}
    if seed==42:
        old=np.load(ROOT/'reports/etapa2/validacao_predicoes.npz')['prob_roubo']
        result['baseline_max_abs_diff']=float(np.max(np.abs(old-p)));result['baseline_reproduced_atol_1e7']=bool(np.allclose(old,p,atol=1e-7,rtol=0))
    dest=MODELS/f'experimentos_etapa3/semente_{seed}';dest.mkdir(parents=True,exist_ok=True)
    model.save(dest/'modelo.keras');json_write(dest/'resultado.json',result)
    json_write(OUT/f'estabilidade_{seed}.json',result);preserve()
    print(f'Semente {seed} concluida: accuracy {result["accuracy"]:.6f}',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,required=True);args=parser.parse_args()
    if args.seed not in [42,7,123]:raise ValueError('Protocolo fixo: apenas 42,7,123')
    run(args.seed)
