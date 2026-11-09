"""Interface Python, sem HTTP. Carregue somente artefatos locais confiaveis."""
from ml.runtime import ROOT,MODELS,FEATURES,LABELS
import json
import joblib
import numpy as np

class ClassificadorOcorrencias:
    def __init__(self,model_dir=MODELS):
        import tensorflow as tf
        from pathlib import Path
        p=Path(model_dir)
        self.config=json.loads((p/'config_modelo.json').read_text(encoding='utf-8'))
        if self.config['features']!=FEATURES:raise ValueError('Lista de entradas do artefato inesperada')
        self.preprocessador=joblib.load(p/'preprocessador.joblib')
        self.model=tf.keras.models.load_model(p/'mlp_baseline.keras',compile=False)
        if self.model.input_shape[-1]!=len(self.preprocessador.feature_names_):raise ValueError('Modelo e preprocessador incompativeis')

    def classificar(self,mes,dia_semana,tipo_local,bairro):
        record=dict(mes=mes,dia_semana=dia_semana,tipo_local=tipo_local,bairro=bairro)
        matrix=self.preprocessador.transform([record])
        prob=float(self.model(matrix.toarray(),training=False).numpy()[0,0])
        label=int(prob>=self.config['threshold'])
        return {'codigo':label,'classe':LABELS[label],'probabilidade_furto':1-prob,'probabilidade_roubo':prob,'probabilidades_calibradas':False}

if __name__=='__main__':
    print(json.dumps(ClassificadorOcorrencias().classificar(5,2,'VIA PÚBLICA','BELA VISTA'),ensure_ascii=False,indent=2))
