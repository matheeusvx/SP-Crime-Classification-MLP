from ml.runtime import ROOT
import numpy as np
from sklearn.metrics import log_loss

def metrics(y,p):
    y=np.asarray(y,dtype=np.int8);p=np.asarray(p,dtype=np.float64)
    if len(y)!=len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not set(np.unique(y))<={0,1}:raise ValueError('Rotulos/probabilidades invalidos')
    tn,fp,fn,tp=np.bincount(y*2+(p>=.5),minlength=4)
    div=lambda a,b:float(a/b) if b else 0.
    f0=div(2*tn,2*tn+fp+fn);f1=div(2*tp,2*tp+fp+fn)
    r={'n':len(y),'furtos':int(tn+fp),'roubos':int(tp+fn),'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp),
      'accuracy':div(tn+tp,len(y)),'precision_roubo':div(tp,tp+fp),'recall_roubo':div(tp,tp+fn),'f1_roubo':f1,
      'precision_furto':div(tn,tn+fn),'recall_furto':div(tn,tn+fp),'f1_furto':f0,
      'macro_f1':(f0+f1)/2,'balanced_accuracy':(div(tn,tn+fp)+div(tp,tp+fn))/2 if (tn+fp) and (tp+fn) else None,
      'brier':float(np.mean((p-y)**2)),'log_loss':float(log_loss(y,p,labels=[0,1])),
      'high_conf_errors':int(np.sum(((p>=.5)!=y)&(np.maximum(p,1-p)>=.9))),
      'high_conf_fn':int(np.sum((y==1)&(p<.5)&(1-p>=.9)))}
    for n in [10,20]:
        ids=np.minimum((p*n).astype(int),n-1)
        r[f'ece{n}']=float(sum(np.mean(ids==i)*abs(np.mean(p[ids==i])-np.mean(y[ids==i])) for i in range(n) if np.any(ids==i)))
    r['confusion_matrix']=[[int(tn),int(fp)],[int(fn),int(tp)]]
    return r

def calibration_bins(y,p,bins=10):
    p=np.asarray(p);y=np.asarray(y);ids=np.minimum((p*bins).astype(int),bins-1)
    return [{'bin':i,'lower':i/bins,'upper':(i+1)/bins,'n':int(np.sum(ids==i)),
      'prob_mean':float(np.mean(p[ids==i])) if np.any(ids==i) else None,
      'roubo_frequency':float(np.mean(y[ids==i])) if np.any(ids==i) else None} for i in range(bins)]

def confidence_intervals(m,seed=12345,reps=10000):
    n=m['n'];cells=np.array([m[k] for k in ['tn','fp','fn','tp']])
    tn,fp,fn,tp=np.random.default_rng(seed).multinomial(n,cells/n,size=reps).T
    values={'accuracy':(tn+tp)/n,'macro_f1':.5*(2*tn/(2*tn+fp+fn)+2*tp/(2*tp+fp+fn)),
      'balanced_accuracy':.5*(tn/(tn+fp)+tp/(tp+fn)),'recall_roubo':tp/(tp+fn)}
    return {k:{'lower':float(np.percentile(v,2.5)),'upper':float(np.percentile(v,97.5)),'point':m[k]} for k,v in values.items()}
