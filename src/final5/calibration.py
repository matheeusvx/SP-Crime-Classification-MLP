"""Platt de duas variaveis escalares a/b; nao modifica a rede."""
import numpy as np
from scipy.special import logit
from sklearn.linear_model import LogisticRegression

class PlattCalibrator:
    def fit(self,prob,y):
        self.estimator=LogisticRegression(C=1e6,solver='lbfgs',max_iter=1000,tol=1e-10,random_state=42)
        self.estimator.fit(logit(np.clip(np.asarray(prob,dtype=np.float64),1e-7,1-1e-7)).reshape(-1,1),y)
        return self
    def transform(self,prob):
        return self.estimator.predict_proba(logit(np.clip(np.asarray(prob,dtype=np.float64),1e-7,1-1e-7)).reshape(-1,1))[:,1]
