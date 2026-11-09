"""Consolidacao sem novos ajustes; todas as configuracoes e resultados inferiores."""
from experiments4.common import *
import numpy as np

def runs():return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT/'runs').glob('*.json'))]
def consolidate():
    preserve();rs=runs();a0=next(r for r in rs if r['run_id']=='A0_internal_s42')
    historical=json.loads((ROOT/'reports/etapa2/metricas_baseline.json').read_text(encoding='utf-8'))
    hist=next(r for r in historical if r['modelo']=='MLP' and r['ano']==2024)
    allrows=[];group_rows=[]
    for r in rs:
        m=r['validation_metrics'];cfg=r['config']
        row={'run_id':r['run_id'],'id':r['id'],'scope':r['scope'],'seed':r['seed'],'features':' + '.join(cfg['features']),
          'min_bairro_count':cfg['min_count'],'local_alias':cfg['local_alias'],'architecture':'→'.join(map(str,cfg['units'])),
          'dropout':cfg['dropout'],'l2':cfg['l2'],'lr':cfg['lr'],'threshold':r['threshold'],'input_dimension':r['input_dimension'],'parameters':r['parameters'],
          'train_n':r['train_n'],'validation_n':r['validation_n'],'epochs':r['epochs_ran'],'best_epoch':r['best_epoch'],'fixed_budget':r['fixed_epoch_budget'],
          'training_seconds':r['training_seconds'],'reused_from':r['reused_from'] or '',**m,
          'train_accuracy':r['train_metrics']['accuracy'],'train_macro_f1':r['train_metrics']['macro_f1'],'train_bce':r['train_metrics']['log_loss'],
          'gap_accuracy':r['train_metrics']['accuracy']-m['accuracy'],'gap_bce':m['log_loss']-r['train_metrics']['log_loss'],
          'retained_bairros':r['preprocess_train']['retained_bairros'],
          'train_rare_bucket':r['preprocess_train'].get('bairro',{}).get('rare_bucket',0),
          'validation_rare_bucket':r['preprocess_validation'].get('bairro',{}).get('rare_bucket',0),
          'validation_unknown_bairros':r['preprocess_validation'].get('bairro',{}).get('unknown',0),
          'delta_macro_f1_pp':100*(m['macro_f1']-(a0['validation_metrics']['macro_f1'] if r['scope']=='internal' else hist['macro_f1'])),
          'delta_recall_pp':100*(m['recall_roubo']-(a0['validation_metrics']['recall_roubo'] if r['scope']=='internal' else hist['recall'])),
          'delta_accuracy_pp':100*(m['accuracy']-(a0['validation_metrics']['accuracy'] if r['scope']=='internal' else hist['accuracy'])),
          'hypothesis':r['hypothesis'],'modified_factor':r['factor'],'status':r['status'],'model_path':r['model_path'],'preprocessor_path':r['preprocessor_path'],
          'environment_path':'reports/etapa4/ambiente.json','plan_hash':r['plan_hash']}
        allrows.append(row)
        group_rows.extend({'run_id':r['run_id'],'id':r['id'],'scope':r['scope'],'seed':r['seed'],**g} for g in r['groups'])
    save('resultados_experimentos',allrows)
    save('comparacao_atributos',[r for r in allrows if r['scope']=='internal' and r['id'].startswith('A')])
    save('comparacao_arquiteturas',[r for r in allrows if r['scope']=='full' and r['id'].startswith('B') and r['seed']==42])
    save('comparacao_regularizacao',[r for r in allrows if r['scope']=='internal' and r['seed']==42 and (r['id'].startswith('C') or r['id']==read('decisao_arquitetura_interna.json')['id'])])
    save('erros_subgrupos',group_rows)
    save('historico_treinamentos',[{'run_id':r['run_id'],'scope':r['scope'],'epoca':i+1,**{k:values[i] for k,values in r['history'].items()}} for r in rs for i in range(r['epochs_ran'])])
    stability=[]
    for scope in ['internal','full']:
        for candidate in read('agenda_reajuste_congelada.json')['candidates']:
            matching=[r for r in rs if r['scope']==scope and r['id']==candidate['id']]
            for metric in ['accuracy','macro_f1','balanced_accuracy','recall_roubo','precision_roubo','brier','log_loss']:
                values=[r['validation_metrics'][metric] for r in matching]
                stability.append({'id':candidate['id'],'scope':scope,'metric':metric,'n_seeds':len(values),'mean':float(np.mean(values)),'sd':float(np.std(values,ddof=1)),'min':min(values),'max':max(values)})
    save('estabilidade',stability)
    full_summary=[]
    for id in sorted({r['id'] for r in rs if r['scope']=='full'}):
        matching=[r for r in rs if r['scope']=='full' and r['id']==id];reference=matching[0]
        full_summary.append({'id':id,'architecture':'→'.join(map(str,reference['config']['units'])),'features':' + '.join(reference['config']['features']),
          'seeds':','.join(str(r['seed']) for r in matching),'n_seeds':len(matching),'parameters':reference['parameters'],'epochs':reference['fixed_epoch_budget'],
          **{metric+'_mean':float(np.mean([r['validation_metrics'][metric] for r in matching])) for metric in ['accuracy','macro_f1','balanced_accuracy','recall_roubo','precision_roubo','brier','log_loss']},
          'macro_f1_sd':float(np.std([r['validation_metrics']['macro_f1'] for r in matching],ddof=1)) if len(matching)>1 else None,
          'macro_delta_historico_pp':100*(float(np.mean([r['validation_metrics']['macro_f1'] for r in matching]))-hist['macro_f1'])})
    save('resumo_validacao_2024',full_summary)
    # Candidato principal de recomendacao: entre as duas estaveis, media de Macro F1 com tolerancia de 0,002 e simplicidade.
    candidates=[r for r in full_summary if r['n_seeds']==3];best=max(candidates,key=lambda r:r['macro_f1_mean'])
    eligible=[r for r in candidates if r['macro_f1_mean']>=best['macro_f1_mean']-.002 and r['recall_roubo_mean']>=best['recall_roubo_mean']-.02]
    main=min(eligible,key=lambda r:r['parameters']);alternative=next(r for r in candidates if r['id']!=main['id'])
    recommendation={'principal':main,'alternativa':alternative,'not_final_selection':True,'used_2025':False,'rule':'Media de 3 sementes, Macro F1 ate .002 e recall ate .02 do melhor; preferir menos parametros; sem novo ajuste apos 2024',
       'experiment_counts':{'logical_runs':len(rs),'fresh_trainings':sum(not r['reused_from'] for r in rs),'reused':sum(bool(r['reused_from']) for r in rs)}}
    json_write(OUT/'recomendacao_candidatos.json',recommendation)
    json_write(OUT/'conclusoes_por_experimento.json',[{'run_id':r['run_id'],'hipotese':r['hypothesis'],'fator':r['factor'],
       'interpretacao':('Comparacao interna em 2023, diferenca de Macro F1 contra A0: ' if r['scope']=='internal' else 'Comparacao em 2024, diferenca contra historico (protocolo diferente): ')+f"{next(x['delta_macro_f1_pp'] for x in allrows if x['run_id']==r['run_id']):+.3f} pp",
       'conclusao':'Referencia/reutilizacao sem novo treinamento' if r['reused_from'] else 'Resultado registrado; nao e vencedor definitivo'} for r in rs])
    print(json.dumps(recommendation,ensure_ascii=False,indent=2));preserve()

if __name__=='__main__':consolidate()
