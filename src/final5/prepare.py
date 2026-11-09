"""Confere 2024, decide calibracao e congela antes de qualquer inferencia de 2025."""
from final5.common import *
from final5.metrics import metrics,calibration_bins
from final5.calibration import PlattCalibrator
from ml.runtime import configure_tf
from ml.evaluate import predict_batched
from experiments4.common import data
import numpy as np,joblib,shutil,sys,platform,importlib.metadata

SOURCE='B64_full_s42'
def prepare():
    preserve()
    if (FINAL/'manifesto.json').exists():verify_manifest();print('Pipeline ja congelado; nenhum novo ajuste de calibracao.');return
    protocol=read('protocolo_previo.json');tf=configure_tf(42)
    source=json.loads((ROOT/f'reports/etapa4/runs/{SOURCE}.json').read_text(encoding='utf-8'))
    for name,h in source['artifact_hashes'].items():
        if sha256(ROOT/name)!=h:raise ValueError('Artefato experimental alterado: '+name)
    cfg=source['config']
    expected={'features':FEATURES,'min_count':50,'local_alias':True,'units':[64],'dropout':0.,'l2':0.,'lr':.001}
    if cfg!=expected or source['seed']!=42 or source['epochs_ran']!=3 or source['input_dimension']!=299:raise ValueError('Configuracao de origem divergente')
    FINAL.mkdir(parents=True,exist_ok=True);(OUT/'private').mkdir(exist_ok=True)
    for origin,destination in [('model_path','modelo.keras'),('preprocessor_path','preprocessador.joblib')]:
        src=ROOT/source[origin];dst=FINAL/destination
        if not dst.exists():shutil.copy2(src,dst)
        if sha256(src)!=sha256(dst):raise ValueError('Copia final difere da origem')
    model=tf.keras.models.load_model(FINAL/'modelo.keras',compile=True);pre=joblib.load(FINAL/'preprocessador.joblib')
    if model.input_shape[-1]!=299 or [x.units for x in model.layers]!=[64,1] or model.count_params()!=19265:raise ValueError('Arquitetura inesperada')
    if model.layers[0].activation.__name__!='relu' or model.layers[1].activation.__name__!='sigmoid' or model.layers[0].kernel_regularizer is not None:raise ValueError('Ativacao/regularizacao divergente')
    if type(model.optimizer).__name__!='Adam' or not np.isclose(float(model.optimizer.learning_rate.numpy()),.001):raise ValueError('Otimizador divergente')
    if pre.features!=FEATURES or not pre.local_alias or pre.min_count!=50 or pre.scope!='completo_2023' or pre.rows!=190124:raise ValueError('Preprocessador divergente')
    vr,y,keys=data(2024);p=predict_batched(model,pre.transform(vr))
    saved=np.load(ROOT/source['prediction_path']);maxdiff=float(np.max(np.abs(p-saved['prob_roubo'])))
    if not np.array_equal(y,saved['y_true']) or not np.allclose(p,saved['prob_roubo'],atol=1e-7,rtol=0):raise ValueError('Previsoes de 2024 nao reproduzidas')
    m=metrics(y,p)
    for name in ['accuracy','macro_f1','balanced_accuracy','recall_roubo']:
        if not np.isclose(m[name],source['validation_metrics'][name],atol=1e-12,rtol=0):raise ValueError('Metrica de 2024 divergente: '+name)
    json_write(OUT/'verificacao_previa_2024.json',{'n':len(y),'max_abs_difference':maxdiff,'metrics':m,'copied_bytes_equal':True,'source_artifact_hashes':source['artifact_hashes'],'checked_at':now()})
    months=np.asarray([r['mes'] for r in vr]);h1=months<=6;h2=months>=7
    calibrator=PlattCalibrator().fit(p[h1],y[h1]);cp=calibrator.transform(p)
    baseline=metrics(y[h2],p[h2]);calibrated=metrics(y[h2],cp[h2]);rows=[]
    for label,mask in [('H2_2024',h2),('Q3_2024',(months>=7)&(months<=9)),('Q4_2024',months>=10)]:
        for kind,probs in [('sigmoid_original',p),('platt_candidato',cp)]:rows.append({'periodo':label,'versao':kind,**metrics(y[mask],probs[mask])})
    checks={'positive_slope':float(calibrator.estimator.coef_[0,0])>0,
      'brier_gain':baseline['brier']-calibrated['brier']>=.001,'log_loss_gain':baseline['log_loss']-calibrated['log_loss']>=.002,
      'ece10_guard':calibrated['ece10']<=baseline['ece10']+.002,'ece20_guard':calibrated['ece20']<=baseline['ece20']+.002,
      'macro_f1_guard':calibrated['macro_f1']>=baseline['macro_f1']-.005,'recall_guard':calibrated['recall_roubo']>=baseline['recall_roubo']-.01}
    for quarter in ['Q3_2024','Q4_2024']:
        a=next(r for r in rows if r['periodo']==quarter and r['versao']=='sigmoid_original');b=next(r for r in rows if r['periodo']==quarter and r['versao']=='platt_candidato')
        checks[quarter+'_brier_guard']=b['brier']<=a['brier']+.0005;checks[quarter+'_loss_guard']=b['log_loss']<=a['log_loss']+.001
    adopted=all(checks.values());decision={'registered_protocol_sha256':sha256(OUT/'protocolo_previo.json'),'decided_at':now(),'fit_rows_H1':int(h1.sum()),'assessment_rows_H2':int(h2.sum()),
      'method':'Platt sobre logit(sigmoid)','slope':float(calibrator.estimator.coef_[0,0]),'intercept':float(calibrator.estimator.intercept_[0]),
      'checks':checks,'adopted':adopted,'threshold':.5,'classification_changes_H2':int(np.sum((p[h2]>=.5)!=(cp[h2]>=.5))),
      'assessment_uncalibrated':baseline,'assessment_calibrated':calibrated,'pipeline_frozen_before_2025':True,
      'limitation':'2024 participou previamente da selecao; H2 e holdout do calibrador, nao independente de todas as decisoes do projeto.'}
    json_write(OUT/'decisao_calibracao.json',decision);save('comparacao_calibracao_2024',rows)
    save('curva_calibracao_H2',[{'versao':kind,**r} for kind,probs in [('sigmoid_original',p),('platt_candidato',cp)] for r in calibration_bins(y[h2],probs[h2])])
    if adopted:joblib.dump(calibrator,FINAL/'calibrador.joblib')
    elif (FINAL/'calibrador.joblib').exists():raise RuntimeError('Calibrador nao selecionado presente: revisar, nao sobrescrever')
    finalp=cp if adopted else p
    json_write(OUT/'metricas_2024_pipeline_final.json',metrics(y,finalp))
    np.savez_compressed(OUT/'private/validacao_2024.npz',y_true=y,prob=finalp,raw_prob=p,months=months)
    # Classe/prevalencia majoritaria exclusivamente do treino da execucao escolhida.
    train=source['train_metrics'];majority=0 if train['furtos']>=train['roubos'] else 1
    config={'model_id':MODEL_ID,'selected_source':SOURCE,'architecture':{'input':299,'hidden':[64],'activations':['relu','sigmoid'],'parameters':19265},
      'features':FEATURES,'labels':{'0':'FURTO','1':'ROUBO'},'threshold':.5,'epochs':3,'seed':42,'batch_order_seed':42,'batch_size':256,
      'optimizer':'Adam','learning_rate':.001,'loss':'binary_crossentropy','dropout':0,'l2':0,'min_bairro_count':50,'local_alias':True,
      'training_years':[2023],'calibration_adopted':adopted,'calibrator':'calibrador.joblib' if adopted else None,
      'majority_class_train':majority,'roubo_prevalence_train':train['roubos']/train['n'],'evaluation_expected_rows':156168,
      'versions':{x:importlib.metadata.version(x) for x in ['tensorflow','keras','numpy','scipy','scikit-learn','joblib','pyarrow','duckdb']},'python':sys.version,'platform':platform.platform()}
    json_write(FINAL/'config_final.json',config)
    json_write(FINAL/'contrato.json',{'features_order':FEATURES,'types':{'mes':'inteiro 1..12 ou None','dia_semana':'inteiro 0..6, segunda=0, ou None','tipo_local':'str ou None','bairro':'str ou None'},
      'extra_fields':'rejeitar','normalization':'Objeto experimental original: NFC, espacos/maiusculas, aliases de bairro ativos no treino e acentuacao univoca de local',
      'missing':'categoria explicita; avisar quando sem suporte no treino','unknown_local':'categoria ausente com aviso','unknown_or_rare_bairro':'bucket raro com aviso','numeric_bairro_text':'normalizacao original para ausente com aviso, numero tipado e rejeitado',
      'output':['classe_estimada','codigo_classe','probabilidade_furto','probabilidade_roubo','versao_modelo','probabilidades_calibradas','avisos']})
    inference_files=['src/final5/common.py','src/final5/pipeline.py','src/final5/calibration.py','src/experiments4/preprocessing.py','src/experiments4/common.py','src/ml/runtime.py','src/ml/preprocessing.py','src/ml/evaluate.py']
    frozen=['modelo.keras','preprocessador.joblib','config_final.json','contrato.json']+(['calibrador.joblib'] if adopted else [])
    manifest={'model_id':MODEL_ID,'frozen_at':now(),'source_run':SOURCE,'source_paths':{'model':source['model_path'],'preprocessor':source['preprocessor_path']},
      'source_hashes':source['artifact_hashes'],'frozen_files':{name:sha256(FINAL/name) for name in frozen},'inference_source_hashes':{name:sha256(ROOT/name) for name in inference_files},
      'architecture':config['architecture'],'features_order':FEATURES,'transformed_features_order':pre.names,'feature_encoding_categories':{f:list(pre.encoder.categories_[i]) for i,f in enumerate(FEATURES)},
      'labels':config['labels'],'threshold':.5,'seed':42,'epochs':3,'batch_size':256,'optimizer':'Adam','learning_rate':.001,'loss':'binary_crossentropy',
      'preprocessing':{'class':'experiments4.preprocessing.ExperimentalPreprocessor','fit_scope':pre.scope,'fit_rows':pre.rows,'fit_keys_hash':pre.fit_keys_hash,'min_count':pre.min_count,'retained_bairros':len(pre.frequent),'local_alias':pre.local_alias,'local_map':pre.local_map,'bairro_aliases':pre.aliases},
      'calibration':{'adopted':adopted,'method':'Platt logit' if adopted else None,'decision_sha256':sha256(OUT/'decisao_calibracao.json'),'fit_period':'H1_2024' if adopted else None},
      'versions':config['versions'],'data_source':'SSP-SP, extrato de celulares subtraidos, municipio Sao Paulo, dados elegiveis da Etapa1',
      'dataset_hashes':source['data_hashes'],'evaluation_protocol_sha256':sha256(OUT/'protocolo_previo.json'),'evaluation_expected_year':2025,'evaluation_expected_rows':156168,
      'selection_reasons':['Escolha explicita do usuario','Estabilidade em tres sementes','Simplicidade sem beneficio consistente de profundidade'],
      'limitations':['Dominio restrito a celulares subtraidos da capital','Possiveis efeitos administrativos de local','Contextos com classes sobrepostas','Mudanca temporal e categorias raras/novas','Demonstracao academica; nao validado para decisoes policiais','Nao determina natureza juridica nem preve crimes futuros'],
      'freeze_before_test_inference':True}
    json_write(FINAL/'manifesto.json',manifest);(FINAL/'manifesto.sha256').write_text(sha256(FINAL/'manifesto.json')+'\n',encoding='ascii')
    verify_manifest();preserve();print(json.dumps({'verification_2024':m,'calibration_decision':decision,'frozen_at':manifest['frozen_at']},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':prepare()
