from ml.runtime import ROOT,FEATURES,MODELS,json_write,sha256
import csv,json
import numpy as np
OUT=ROOT/'reports/etapa3'
FIG=OUT/'figures'
MIN_SUPPORT=200

def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def save(name,rows):
    path=OUT/(name+'.csv');path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def preserve():
    path=OUT/'preservacao.json'
    if not path.exists():
        paths=[]
        for folder in ['data/processed','data/interim','src/data','src/ml','reports','models','notebooks','docs']:
            paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'tmp' not in p.parts and 'etapa3' not in p.parts and 'experimentos_etapa3' not in p.parts and 'etapa3' not in p.name and '03_' not in p.name and 'etapa4' not in p.name)
        paths.extend(ROOT/p for p in ['tests/test_integridade.py','tests/test_ml_pipeline.py','README.md','requirements.txt','requirements-ml.txt','.gitignore'])
        json_write(path,{p.relative_to(ROOT).as_posix():sha256(p) for p in paths})
    changed=[p for p,h in read('preservacao.json').items() if sha256(ROOT/p)!=h]
    if changed:raise RuntimeError(f'Artefatos anteriores alterados: {changed}')
    return len(read('preservacao.json'))

def metrics(y,p):
    pred=p>=.5;tn,fp,fn,tp=np.bincount(np.asarray(y,dtype=int)*2+pred.astype(int),minlength=4)
    div=lambda a,b:float(a/b) if b else 0.0
    f0=div(2*tn,2*tn+fp+fn);f1=div(2*tp,2*tp+fp+fn)
    return dict(n=len(y),furtos=int(sum(y==0)),roubos=int(sum(y==1)),tn=int(tn),fp=int(fp),fn=int(fn),tp=int(tp),
       accuracy=div(tn+tp,len(y)),macro_f1=(f0+f1)/2,
       balanced_accuracy=(div(tn,tn+fp)+div(tp,tp+fn))/2 if (tn+fp) and (tp+fn) else None,
       precision_roubo=div(tp,tp+fp),recall_roubo=div(tp,tp+fn),f1_roubo=f1)

def load():
    from ml.dataset import connection,load_year
    from ml.inference import ClassificadorOcorrencias
    from ml.evaluate import predict_batched
    c=connection();tr,y,keys=load_year(c,2023);vr,vy,vkeys=load_year(c,2024)
    assert not(set(keys)&set(vkeys))
    model=ClassificadorOcorrencias();pre=model.preprocessador
    # Confronta apenas os anos autorizados com a base analitica por chave.
    mismatch=c.sql('''SELECT count(*) FROM indexed b JOIN meta m USING(indice_linha) JOIN analytic a USING(chave_bo)
      WHERE m.ano_fato IN (2023,2024) AND (b.mes IS DISTINCT FROM a.mes OR b.dia_semana IS DISTINCT FROM a.dia_semana
      OR b.tipo_local IS DISTINCT FROM a.tipo_local OR b.bairro IS DISTINCT FROM a.bairro OR b.alvo IS DISTINCT FROM a.alvo
      OR m.data_fato IS DISTINCT FROM a.data_fato OR year(m.data_fato)!=m.ano_fato)''').fetchall()[0][0]
    assert mismatch==0
    X=pre.transform(tr);V=pre.transform(vr)
    p=predict_batched(model.model,V)
    saved=np.load(ROOT/'reports/etapa2/validacao_predicoes.npz')
    assert np.array_equal(vy,saved['y_true']) and np.allclose(p,saved['prob_roubo'],atol=1e-7,rtol=0)
    assert metrics(vy,p)['tn']==68328 and metrics(vy,p)['fp']==23727 and metrics(vy,p)['fn']==25962 and metrics(vy,p)['tp']==40878
    return tr,y,keys,vr,vy,vkeys,model,X,V,p
