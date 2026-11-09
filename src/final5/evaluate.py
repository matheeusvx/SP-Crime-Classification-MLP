"""Uma unica inferencia planejada em 2025; testes posteriores usam cache privado."""
from final5.common import *
from final5.metrics import metrics,confidence_intervals,calibration_bins
import numpy as np,time,traceback
from pathlib import Path

def approve_test_access():
    m=verify_manifest();preserve();pre=read('testes_previos.json')
    if not pre['passed'] or pre['manifest_sha256']!=sha256(FINAL/'manifesto.json') or sum(r['executados'] for r in pre['suites'])<57:
        raise RuntimeError('Testes previos aprovados para este manifesto sao obrigatorios')
    if sha256(OUT/'decisao_calibracao.json')!=m['calibration']['decision_sha256'] or sha256(OUT/'protocolo_previo.json')!=m['evaluation_protocol_sha256']:
        raise RuntimeError('Decisao ou protocolo alterado depois do congelamento')
    return m,pre

def load_test():
    approve_test_access()
    # Excecao final deliberada ao bloqueio dos carregadores de desenvolvimento.
    from ml.dataset import connection
    c=connection()
    for name,h in verify_manifest()['dataset_hashes'].items():
        if sha256(ROOT/f'data/processed/{name}.parquet')!=h:raise RuntimeError('Dataset processado mudou')
    sql='''FROM indexed b JOIN meta m USING(indice_linha) JOIN analytic a USING(chave_bo) WHERE year(m.data_fato)=2025'''
    mismatch=c.sql('''SELECT count(*) '''+sql+''' AND (b.mes IS DISTINCT FROM a.mes OR b.dia_semana IS DISTINCT FROM a.dia_semana
       OR b.tipo_local IS DISTINCT FROM a.tipo_local OR b.bairro IS DISTINCT FROM a.bairro OR b.alvo IS DISTINCT FROM a.alvo
       OR m.data_fato IS DISTINCT FROM a.data_fato OR m.ano_fato!=2025 OR m.municipio_ibge!='3550308'
       OR a.municipio_ibge!='3550308' OR b.mes!=month(m.data_fato) OR b.dia_semana!=isodow(m.data_fato)-1
       OR b.alvo IS NULL OR b.alvo NOT IN (0,1))''').fetchall()[0][0]
    t=c.sql('SELECT '+','.join('b.'+f for f in FEATURES)+',b.alvo,m.chave_bo,m.indice_linha '+sql+' ORDER BY m.indice_linha').to_arrow_table()
    keys=t['chave_bo'].to_pylist()
    overlap=c.sql('''SELECT count(*) FROM (SELECT chave_bo FROM meta GROUP BY 1 HAVING count(DISTINCT year(data_fato))>1)''').fetchall()[0][0]
    if mismatch or overlap or len(keys)!=156168 or len(set(keys))!=len(keys):raise ValueError('Integridade de 2025 falhou; nao inferir')
    records=t.select(FEATURES).to_pylist();y=np.asarray(t['alvo'].to_numpy(),dtype=np.int8)
    if set(np.unique(y))!={0,1}:raise ValueError('Rotulos finais invalidos')
    from ml.preprocessing import digest_keys
    proof={'n':len(y),'alignment_mismatches':int(mismatch),'overlap_between_years':int(overlap),'unique_keys':len(set(keys)),
      'test_keys_sha256':digest_keys(keys),'checked_at':now(),'dataset_hashes':verify_manifest()['dataset_hashes']}
    c.close();return records,y,proof

def subgroup_metrics(records,y,p,pre):
    from ml.preprocessing import MISSING
    raw=np.asarray([pre._raw(r) for r in records],dtype=object)
    conditions=[]
    for row in raw:
        b=row[3];conditions.append('ausente' if b==MISSING else 'frequente' if b in pre.frequent else 'raro_conhecido' if b in pre.known['bairro'] else 'desconhecido')
    groups={'mes':[str(r['mes']) for r in records],'tipo_local':[r['tipo_local'] if r['tipo_local'] is not None else '(AUSENTE)' for r in records],
      'condicao_bairro':conditions,'presenca_local':['ausente' if row[2]==MISSING else 'preenchido' for row in raw],
      'algum_atributo_ausente':['sim' if MISSING in row else 'nao' for row in raw]}
    output=[]
    for name,values in groups.items():
        values=np.asarray(values,dtype=object)
        for category in sorted(set(values),key=str):
            mask=values==category;m=metrics(y[mask],p[mask])
            output.append({'grupo':name,'categoria':category,**m,'destacar':m['n']>=200 and min(m['furtos'],m['roubos'])>=30})
    return output,pre.describe(records)

def evaluate_once():
    m,precheck=approve_test_access();state=OUT/'avaliacao_unica.json'
    if state.exists():
        s=read('avaliacao_unica.json')
        if s['status']=='completed':
            for p,h in s['result_hashes'].items():
                if sha256(ROOT/p)!=h:raise RuntimeError('Resultados finais alterados')
            print('Avaliacao final ja concluida: resultados em cache; nenhuma nova inferencia.');return
        raise RuntimeError('Existe uma tentativa anterior incompleta/falha; investigar o registro, sem repeticao automatica')
    initial={'status':'started','evaluation_id':MODEL_ID+'-teste-2025-unico','started_at':now(),'manifest_sha256':sha256(FINAL/'manifesto.json'),
      'frozen_at':m['frozen_at'],'pretests_sha256':sha256(OUT/'testes_previos.json'),'prediction_calls':0,'test_year':2025,'model_version':MODEL_ID,
      'evaluation_code_sha256':sha256(Path(__file__)),'metrics_code_sha256':sha256(ROOT/'src/final5/metrics.py'),'tensorflow_seed':42,'bootstrap_seed':12345}
    with state.open('x',encoding='utf-8') as f:json.dump(initial,f,ensure_ascii=False,indent=2)
    start=time.perf_counter()
    try:
        from final5.pipeline import FinalPipeline
        from ml.runtime import configure_tf
        configure_tf(42);pipeline=FinalPipeline()
        records,y,integrity=load_test()
        initial|={'integrity_verified_at':now(),'inference_started_at':now(),'prediction_calls':1};json_write(state,initial)
        p=pipeline.probabilities(records) # unica passagem pelos 156.168 BOs
        result=metrics(y,p);ci=confidence_intervals(result)
        config=json.loads((FINAL/'config_final.json').read_text(encoding='utf-8'))
        reference=metrics(y,np.full(len(y),config['roubo_prevalence_train']))
        groups,category_stats=subgroup_metrics(records,y,p,pipeline.preprocessor)
        # Diagnostico de mudanca de distribuicao, realizado somente apos congelamento.
        from experiments4.common import data
        vr,vy,_=data(2024)
        raw2024=np.asarray([pipeline.preprocessor._raw(r) for r in vr],dtype=object)
        raw2025=np.asarray([pipeline.preprocessor._raw(r) for r in records],dtype=object)
        import collections
        drift=[];missing=[]
        for j,field in enumerate(FEATURES):
            a=collections.Counter(raw2024[:,j]);b=collections.Counter(raw2025[:,j]);n4=len(vr);n5=len(records)
            drift.append({'atributo':field,'total_variation':.5*sum(abs(a[k]/n4-b[k]/n5) for k in set(a)|set(b)),
              'levels_2024':len(a),'levels_2025':len(b),'new_vs_2024_levels':len(set(b)-set(a)),'new_vs_2024_records':sum(b[k] for k in set(b)-set(a))})
            from ml.preprocessing import MISSING
            for year,raw,labels in [(2024,raw2024,vy),(2025,raw2025,y)]:
                for label in [0,1]:
                    mask=labels==label;missing.append({'ano':year,'atributo':field,'classe':label,'n':int(np.sum(mask)),'ausentes':int(np.sum(raw[mask,j]==MISSING)),
                      'taxa_ausencia':float(np.mean(raw[mask,j]==MISSING))})
        temporal=[{'ano':2024,**read('metricas_2024_pipeline_final.json')},{'ano':2025,**result}]
        OUT.joinpath('private').mkdir(exist_ok=True)
        np.savez_compressed(OUT/'private/previsoes_2025.npz',y_true=y,prob=p,months=np.asarray([r['mes'] for r in records],dtype=np.int8))
        json_write(OUT/'metricas_2025.json',result);json_write(OUT/'referencia_majoritaria_2025.json',{'class_from_train':config['majority_class_train'],
          'probability_from_train':config['roubo_prevalence_train'],'test_labels_used_to_choose_class':False,'metrics':reference})
        json_write(OUT/'intervalos_confianca_2025.json',{'method':read('protocolo_previo.json')['bootstrap'],'metrics':ci})
        json_write(OUT/'categorias_2025.json',category_stats)
        save('comparacao_2024_2025',temporal);save('metricas_grupos_2025',groups);save('calibracao_bins_2025',calibration_bins(y,p))
        save('mudanca_distribuicao_2024_2025',drift);save('ausencias_ano_classe',missing)
        json_write(OUT/'verificacao_integridade.json',integrity|{'manifest_sha256':sha256(FINAL/'manifesto.json'),'frozen_files':m['frozen_files'],'final_hashes_unchanged':True,
          'pipeline_adjusted_on_test':False,'training_on_2025':False,'test_inference_after_freeze':initial['inference_started_at']>m['frozen_at']})
        verify_manifest();preserve()
        result_paths=[OUT/'metricas_2025.json',OUT/'private/previsoes_2025.npz',OUT/'intervalos_confianca_2025.json',OUT/'verificacao_integridade.json',OUT/'comparacao_2024_2025.csv',OUT/'metricas_grupos_2025.csv',OUT/'referencia_majoritaria_2025.json',OUT/'categorias_2025.json',OUT/'mudanca_distribuicao_2024_2025.csv',OUT/'ausencias_ano_classe.csv',OUT/'calibracao_bins_2025.csv']
        json_write(state,initial|{'status':'completed','completed_at':now(),'seconds':time.perf_counter()-start,'result_hashes':{x.relative_to(ROOT).as_posix():sha256(x) for x in result_paths}})
        print(json.dumps({'metrics_2025':result,'majority_reference':reference,'confidence_intervals':ci,'integrity':integrity},ensure_ascii=False,indent=2),flush=True)
    except Exception:
        json_write(state,initial|{'status':'failed','failed_at':now(),'error':traceback.format_exc(),'automatic_retry_allowed':False})
        raise

if __name__=='__main__':evaluate_once()
