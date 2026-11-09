"""Erros, deslocamento, permutacao agrupada e calibracao sem ajustar modelo."""
from diagnostics.common import *
from ml.runtime import configure_tf
from ml.evaluate import predict_batched
from ml.preprocessing import MISSING
import collections,pickle
from sklearn.metrics import brier_score_loss,log_loss,precision_score,recall_score,f1_score

def group_metrics(groups,y,p,attribute):
    out=[];groups=np.asarray(groups,dtype=object)
    for category in sorted(set(groups),key=str):
        ids=np.flatnonzero(groups==category);m=metrics(y[ids],p[ids]);n=len(ids)
        err=(p[ids]>=.5)!=y[ids]
        # Wilson 95% para taxa de erro; intervalo descritivo, nao corrige comparacoes multiplas.
        rate=float(np.mean(err));z=1.95996398454;den=1+z*z/n
        center=(rate+z*z/(2*n))/den;half=z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/den
        out.append({'atributo':attribute,'categoria':category,**m,'taxa_erro':rate,'erro_ic95_inf':center-half,'erro_ic95_sup':center+half,
          'fpr':m['fp']/m['furtos'] if m['furtos'] else None,'fnr':m['fn']/m['roubos'] if m['roubos'] else None,
          'prob_roubo_media':float(p[ids].mean()),'prob_media_FN':float(p[ids][(y[ids]==1)&(p[ids]<.5)].mean()) if m['fn'] else None,
          'prob_media_FP':float(p[ids][(y[ids]==0)&(p[ids]>=.5)].mean()) if m['fp'] else None,
          'destacar':n>=MIN_SUPPORT and min(m['furtos'],m['roubos'])>=30})
    return out

def analyze():
    OUT.mkdir(parents=True,exist_ok=True);preserve();tf=configure_tf()
    tr,y,keys,vr,vy,vkeys,clf,X,V,p=load();pre=clf.preprocessador
    pre_before=pickle.dumps(pre)
    assert [l.units for l in clf.model.layers]==[64,1] and clf.model.count_params()==19265
    summary={'validacao':metrics(vy,p),'architecture':{'input':clf.model.input_shape[-1],'units':[l.units for l in clf.model.layers],'params':clf.model.count_params()},'threshold':clf.config['threshold'],'years':[2023,2024]}
    n=len(vy);normalized={year:np.asarray([pre._normalize(r) for r in records],dtype=object) for year,records in [(2023,tr),(2024,vr)]}
    def condition(v):return 'ausente' if v==MISSING else 'frequente' if v in pre.frequent_bairros_ else 'raro_conhecido' if v in pre.known_bairros_ else 'desconhecido'
    groups=[]
    for feature in FEATURES:groups+=group_metrics([r[feature] if r[feature] is not None else '(AUSENTE)' for r in vr],vy,p,feature)
    cond=[condition(v) for v in normalized[2024][:,3]]
    groups+=group_metrics(cond,vy,p,'condicao_bairro')
    counts=[pre.bairro_counts_.get(v,0) for v in normalized[2024][:,3]]
    bins=['ausente' if v==MISSING else '0/novo' if v not in pre.known_bairros_ else '1–9' if count<10 else '10–49' if count<50 else '50–499' if count<500 else '500+' for v,count in zip(normalized[2024][:,3],counts)]
    groups+=group_metrics(bins,vy,p,'frequencia_bairro_treino')
    groups+=group_metrics(['ausente' if v==MISSING else 'preenchido' for v in normalized[2024][:,2]],vy,p,'presenca_local')
    groups+=group_metrics(['nenhum' if MISSING not in row else 'algum_ausente' for row in normalized[2024]],vy,p,'ausencias')
    groups+=group_metrics([(r['mes']-1)//3+1 for r in vr],vy,p,'trimestre')
    save('metricas_grupos',[g for g in groups if g['atributo']!='bairro' or g['destacar']])
    save('analise_erros',[g for g in groups if g['atributo']!='bairro' or g['destacar']])
    # Todos os niveis publicos agregados; sem BOs individuais.
    shift=[];missing=[];cross=[];new=[];distributions=[]
    for j,feature in enumerate(FEATURES):
        a=normalized[2023][:,j];b=normalized[2024][:,j];ca=collections.Counter(a);cb=collections.Counter(b);cats=set(ca)|set(cb)
        tv=.5*sum(abs(ca[k]/len(a)-cb[k]/len(b)) for k in cats)
        for k in cats:
            distributions.append({'atributo':feature,'categoria':k,'n_2023':ca[k],'pct_2023':ca[k]/len(a),'n_2024':cb[k],'pct_2024':cb[k]/len(b)})
            if cb[k] and not ca[k]:new.append({'atributo':feature,'categoria':k,'n_2024':cb[k]})
            for year,values,labels in [(2023,a,y),(2024,b,vy)]:
                ids=values==k;size=int(sum(ids))
                if size:cross.append({'ano':year,'atributo':feature,'categoria':k,'n':size,'roubos':int(sum(labels[ids]==1)),'taxa_roubo':float(np.mean(labels[ids])),'destacar':size>=MIN_SUPPORT})
        shift.append({'atributo':feature,'distancia_variacao_total':tv,'categorias_2023':len(ca),'categorias_2024':len(cb),'novas_2024':len(set(cb)-set(ca)),'registros_novos_2024':sum(cb[k] for k in set(cb)-set(ca))})
        for year,values,labels in [(2023,a,y),(2024,b,vy)]:
            for label in [0,1]:
                ids=labels==label;missing.append({'ano':year,'atributo':feature,'classe':label,'n':int(sum(ids)),'ausentes':int(sum(values[ids]==MISSING)),'taxa_ausencia':float(np.mean(values[ids]==MISSING))})
    save('drift_atributos',shift);save('categorias_novas_2024',new);save('distribuicoes_anos',distributions);save('ausencias_ano_classe',missing);save('relacoes_categoria_rotulo',cross)
    # Confianca da classe prevista, probabilidade da classe verdadeira e confiabilidade P(ROUBO).
    correct=(p>=.5)==vy;confidence=np.maximum(p,1-p);truthprob=np.where(vy==1,p,1-p)
    confidence_rows=[]
    for name,mask in [('todos',np.ones(n,dtype=bool)),('corretos',correct),('incorretos',~correct),('FP',(vy==0)&(p>=.5)),('FN',(vy==1)&(p<.5))]:
        confidence_rows.append({'grupo':name,'n':int(sum(mask)),'confianca_media':float(confidence[mask].mean()),'prob_classe_verdadeira_media':float(truthprob[mask].mean()),'mediana_prob_roubo':float(np.median(p[mask])),
            **{f'n_confianca_ge_{t}':int(sum(mask&(confidence>=t))) for t in [.8,.9,.95]}})
    save('confianca',confidence_rows)
    calibration=[]
    for bins_n in [10,20]:
        ids=np.minimum((p*bins_n).astype(int),bins_n-1);ece=0
        for i in range(bins_n):
            mask=ids==i;size=int(sum(mask))
            mean=float(np.mean(p[mask])) if size else None;freq=float(np.mean(vy[mask])) if size else None
            if size:ece+=size/n*abs(mean-freq)
            calibration.append({'bins':bins_n,'bin':i,'inferior':i/bins_n,'superior':(i+1)/bins_n,'n':size,'prob_media':mean,'freq_roubo':freq})
        summary[f'ece_{bins_n}']=ece
    summary['brier']=float(brier_score_loss(vy,p));summary['log_loss']=float(log_loss(vy,p));summary['prob_roubo_media']=float(p.mean());summary['prevalencia_roubo']=float(vy.mean())
    summary['brier_constante_prevalencia_treino']=float(brier_score_loss(vy,np.full(n,y.mean())))
    save('calibracao_bins',calibration)
    thresholds=[]
    for t in np.linspace(.05,.95,19):
        pred=p>=t
        thresholds.append({'limiar':float(t),'precision_roubo':float(precision_score(vy,pred,zero_division=0)),'recall_roubo':float(recall_score(vy,pred,zero_division=0)),'f1_roubo':float(f1_score(vy,pred,zero_division=0)),'previsoes_roubo':int(sum(pred))})
    save('limiares_diagnosticos',thresholds)
    # Permutacao de todos os dummies de um atributo conjuntamente: embaralha coluna original.
    # Amostra aleatoria simples fixa (30 mil), 5 repeticoes, sem ajuste; baseline da MESMA amostra.
    rng=np.random.default_rng(314159);sample=np.sort(rng.choice(n,min(30000,n),replace=False));sr=[vr[i] for i in sample];sy=vy[sample];sp=p[sample];base=metrics(sy,sp)
    imp=[]
    for feature in FEATURES:
        for repeat in range(5):
            order=np.random.default_rng(4200+repeat).permutation(len(sr));altered=[r|{feature:sr[order[i]][feature]} for i,r in enumerate(sr)]
            pp=predict_batched(clf.model,pre.transform(altered));m=metrics(sy,pp)
            imp.append({'atributo':feature,'repeticao':repeat+1,'n':len(sr),'delta_macro_f1':base['macro_f1']-m['macro_f1'],'delta_balanced_accuracy':base['balanced_accuracy']-m['balanced_accuracy'],'delta_accuracy':base['accuracy']-m['accuracy']})
        print('Permutacao concluida:',feature,flush=True)
    save('importancia_repeticoes',imp)
    save('importancia_atributos',[{'atributo':f,**{k+'_media':float(np.mean([r[k] for r in imp if r['atributo']==f])) for k in ['delta_macro_f1','delta_balanced_accuracy','delta_accuracy']},'delta_macro_f1_dp':float(np.std([r['delta_macro_f1'] for r in imp if r['atributo']==f],ddof=1))} for f in FEATURES])
    summary['permutation']={'sample_size':len(sr),'sampling_seed':314159,'repeats':5,'same_sample_baseline':base,'limitations':'Marginal, nao causal; quebra dependencias e produz combinacoes artificiais; DP entre permutacoes nao e IC populacional.'}
    # Descricao empirica da ambiguidade em X codificado; nao e novo classificador.
    ambiguity=[]
    for year,mat,labels in [(2023,X,y),(2024,V,vy)]:
        buckets=collections.defaultdict(lambda:[0,0])
        for i,label in enumerate(labels):buckets[tuple(mat.indices[mat.indptr[i]:mat.indptr[i+1]])][int(label)]+=1
        ambiguity.append({'ano':year,'tuplas_codificadas':len(buckets),'tuplas_com_ambas_classes':sum(min(v)>0 for v in buckets.values()),'teto_empirico_acuracia_mesmo_conjunto':sum(max(v) for v in buckets.values())/len(labels)})
    save('ambiguidade_contextos',ambiguity)
    assert pre_before==pickle.dumps(pre)
    json_write(OUT/'resumo.json',summary)
    json_write(OUT/'acesso_dados.json',{'diagnostic_years':[2023,2024],'prediction_years':[2023,2024],'test_2025_predictions':0,'test_2025_transformations':0,'baseline_changed':False,'threshold':.5,'preprocessor_refitted':False})
    preserve();print('Diagnosticos principais concluidos',flush=True)

if __name__=='__main__':analyze()
