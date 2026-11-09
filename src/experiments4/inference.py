"""Inferencia Python de um experimento explicito; nenhum candidato e promovido."""
from experiments4.common import ROOT
import json,joblib
class ExperimentalPredictor:
    def __init__(self,result_path):
        import tensorflow as tf
        from pathlib import Path
        self.result=json.loads(Path(result_path).read_text(encoding='utf-8'))
        self.pre=joblib.load(ROOT/self.result['preprocessor_path'])
        self.model=tf.keras.models.load_model(ROOT/self.result['model_path'],compile=False)
        if self.model.input_shape[-1]!=len(self.pre.names):raise ValueError('Artefatos incompativeis')
    def predict(self,**features):
        x=self.pre.transform([features]);p=float(self.model(x.toarray(),training=False).numpy()[0,0])
        return {'codigo':int(p>=.5),'classe':'ROUBO' if p>=.5 else 'FURTO','probabilidade_roubo':p,'probabilidade_furto':1-p,'calibrada':False}
