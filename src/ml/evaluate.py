"""Metricas de treino/validacao; bloqueia explicitamente o ano reservado."""
from ml.runtime import LABELS
import numpy as np
from sklearn.metrics import accuracy_score,precision_recall_fscore_support,f1_score,balanced_accuracy_score,confusion_matrix,log_loss

def predict_batched(model,matrix,batch_size=256):
    return np.concatenate([model(matrix[i:i+batch_size].toarray(),training=False).numpy().reshape(-1)
                           for i in range(0,matrix.shape[0],batch_size)])

def evaluate(y,prob,*,year,name,threshold=.5):
    if year not in (2023,2024):raise ValueError('Avaliacao de 2025 proibida na Etapa 2')
    pred=(np.asarray(prob)>=threshold).astype(np.int8)
    p,r,f,s=precision_recall_fscore_support(y,pred,labels=[0,1],zero_division=0)
    return {'modelo':name,'ano':year,'n':len(y),'accuracy':float(accuracy_score(y,pred)),
       'precision':float(p[1]),'recall':float(r[1]),'f1':float(f[1]),
       'macro_f1':float(f1_score(y,pred,average='macro',zero_division=0)),
       'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
       'log_loss':float(log_loss(y,prob,labels=[0,1])),
       'por_classe':{LABELS[k]:{'precision':float(p[k]),'recall':float(r[k]),'f1':float(f[k]),'suporte':int(s[k]),'previsoes':int(sum(pred==k))} for k in (0,1)},
       'matriz_confusao':confusion_matrix(y,pred,labels=[0,1]).tolist()}
