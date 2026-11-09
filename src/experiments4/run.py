from experiments4.common import *
from experiments4.engine import Engine,canonical,digest
from experiments4.plan import configs
import argparse,numpy as np

def better(results,tolerance=.002):
    best=max(results,key=lambda r:r['validation_metrics']['macro_f1']);m=best['validation_metrics']
    eligible=[r for r in results if r['validation_metrics']['macro_f1']>=m['macro_f1']-tolerance and r['validation_metrics']['recall_roubo']>=m['recall_roubo']-.02]
    return min(eligible,key=lambda r:(r['parameters'],r['validation_metrics']['log_loss']))

def block_a():
    e=Engine();cfg=configs();rs=[]
    for id in ['A0','A1','A2','A3','A4_10','A4_100']:rs.append(e.run(id,cfg[id]))
    rs.append(e.run('A5',cfg['A5'],reuse='A0_internal_s42'))
    best=max(rs,key=lambda r:r['validation_metrics']['macro_f1']);b=best['validation_metrics']
    eligible=[r for r in rs if r['validation_metrics']['macro_f1']>=b['macro_f1']-.002 and r['validation_metrics']['recall_roubo']>=b['recall_roubo']-.02]
    selected=min(eligible,key=lambda r:('tipo_local' in r['config']['features'],'mes' in r['config']['features'],r['input_dimension'],not r['config']['local_alias']))
    planned_id=selected['id'];a0=next(r for r in rs if r['id']=='A0')
    recall_guard=(selected['validation_metrics']['recall_roubo']<a0['validation_metrics']['recall_roubo']-.02
      and selected['validation_metrics']['macro_f1']<=a0['validation_metrics']['macro_f1']+.002)
    if recall_guard:selected=next(r for r in rs if r['id']=='A5')
    selected_config=selected['config'].copy()
    if 'tipo_local' in selected_config['features']:selected_config['local_alias']=True
    decision={'source_id':selected['id'],'config':selected_config,'internal_macro_f1':selected['validation_metrics']['macro_f1'],'best_internal_macro_f1':b['macro_f1'],
      'eligible_ids':[r['id'] for r in eligible],'selection_rule':'tolerancia .002 Macro F1 / .02 recall, preferir sem local, sem mes, menor dimensao',
      'planned_tiebreak_id':planned_id,'recall_review_override':recall_guard,
      'review_reason':'Regra qualitativa exigida pelo usuario: ganho inferior a .002 Macro F1 nao compensa perda de recall superior a .02 contra A0. Rever antes do Bloco B, sem acrescentar tentativas.',
      'A5_alias_rule':'Correspondencia univoca de acentuacao aprendida no treino; matrizes A5 e A0 identicas. Adotado apenas se local presente.',
      'before_block_B':True,'used_2024':False}
    json_write(OUT/'decisao_representacao.json',decision);print(json.dumps(decision,ensure_ascii=False,indent=2),flush=True);preserve()

def block_bc():
    d=read('decisao_representacao.json');spec=d['config'];e=Engine();bs=[]
    for id,units in [('B32',[32]),('B64',[64]),('B64_32',[64,32])]:
        bs.append(e.run(id,spec|{'units':units,'hypothesis':'Efeito da capacidade na mesma representacao','factor':str(units)}))
    chosen=better(bs);base=chosen['config'];json_write(OUT/'decisao_arquitetura_interna.json',{'id':chosen['id'],'config':base,'rule':'Macro F1 ate .002, recall ate .02, preferir menos parametros','used_2024':False})
    cs=[e.run('C_dropout',base|{'dropout':.1,'hypothesis':'Dropout reduz sobreajuste','factor':'dropout .1'}),e.run('C_l2',base|{'l2':.0001,'hypothesis':'L2 reduz sobreajuste','factor':'L2 .0001'})]
    losses=np.asarray(chosen['history']['val_loss']);osc=bool(len(losses)>=5 and np.any(np.convolve((np.abs(np.diff(losses))>.01).astype(int),np.ones(4,dtype=int),mode='valid')>=4))
    if osc:cs.append(e.run('C_lr',base|{'lr':.0005,'hypothesis':'Oscilacao interna justifica LR menor','factor':'learning rate .0005'}))
    json_write(OUT/'condicao_learning_rate.json',{'condition_met':osc,'executed':osc,'rule':'quatro oscilacoes consecutivas >.01 em val_loss'})
    pool=bs+cs;first=better(pool);others=[r for r in pool if r['id']!=first['id']];different=[r for r in others if r['config']['units']!=first['config']['units'] and r['validation_metrics']['macro_f1']>=first['validation_metrics']['macro_f1']-.005]
    second=better(different if different else others);candidates=[first,second]
    for r in candidates:
        for seed in [7,123]:e.run(r['id'],r['config']|{'hypothesis':r['hypothesis'],'factor':r['factor']},seed=seed)
    selected=[]
    for r in candidates:
        repeats=[read(f'runs/{r["id"]}_internal_s{seed}.json') for seed in [42,7,123]]
        budget=int(np.floor(np.median([x['best_epoch'] for x in repeats])+.5))
        selected.append({'id':r['id'],'config':r['config'],'fixed_epochs':budget,'internal_macro_f1_mean':float(np.mean([x['validation_metrics']['macro_f1'] for x in repeats])),
          'internal_macro_f1_sd':float(np.std([x['validation_metrics']['macro_f1'] for x in repeats],ddof=1))})
    # Congela toda a agenda completa antes da primeira leitura preditiva de 2024.
    agenda={r['id']:{'id':r['id'],'config':r['config'],'fixed_epochs':r['best_epoch'],'seeds':[42]} for r in bs}
    for id in ['A0','A1']:
        r=read(f'runs/{id}_internal_s42.json');agenda[id]={'id':id,'config':r['config'],'fixed_epochs':r['best_epoch'],'seeds':[42]}
    for r in selected:agenda[r['id']]=r|{'seeds':[42,7,123]}
    freeze={'candidates':selected,'agenda':list(agenda.values()),'before_2024_prediction':True,'used_2024_for_budget':False,'protocol':'No further experiments after viewing 2024'}
    json_write(OUT/'agenda_reajuste_congelada.json',freeze);print('Agenda completa congelada antes de avaliar 2024.',flush=True);preserve()

def refit():
    agenda=read('agenda_reajuste_congelada.json');e=Engine()
    for r in agenda['agenda']:
        for seed in r['seeds']:e.run(r['id'],r['config']|{'hypothesis':'Reajuste de candidato congelado na validacao interna','factor':'protocolo completo 2023 com epocas fixas'},scope='full',seed=seed,epochs=r['fixed_epochs'])
    json_write(OUT/'acesso_dados.json',{'fit_internal_months':list(range(1,10)),'validation_internal_months':[10,11,12],'refit_years':[2023],'comparison_years':[2024],'test_2025_predictions':0,'test_2025_transformations':0,'threshold':.5,'calibrated':False})
    preserve()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('block',choices=['A','BC','refit']);a=p.parse_args()
    {'A':block_a,'BC':block_bc,'refit':refit}[a.block]()
