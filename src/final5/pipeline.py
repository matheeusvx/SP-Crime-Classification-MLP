"""Interface reutilizavel final; somente artefatos congelados, sem datasets."""
from final5.common import FINAL,FEATURES,verify_manifest
from ml.preprocessing import MISSING
import joblib
import numpy as np

class FinalPipeline:
    def __init__(self,model_dir=FINAL):
        import tensorflow as tf
        from pathlib import Path
        self.folder=Path(model_dir);self.manifest=verify_manifest(self.folder)
        self.preprocessor=joblib.load(self.folder/'preprocessador.joblib')
        self.model=tf.keras.models.load_model(self.folder/'modelo.keras',compile=False)
        self.calibrator=joblib.load(self.folder/'calibrador.joblib') if self.manifest['calibration']['adopted'] else None
        if self.preprocessor.features!=FEATURES or self.model.input_shape[-1]!=len(self.preprocessor.names) or len(self.preprocessor.names)!=299:
            raise ValueError('Modelo, esquema e preprocessador incompativeis')
    def probabilities(self,records):
        from ml.evaluate import predict_batched
        if not records:return np.empty(0,dtype=np.float64)
        matrix=self.preprocessor.transform(records)
        p=predict_batched(self.model,matrix)
        p=self.calibrator.transform(p) if self.calibrator is not None else p
        if not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise RuntimeError('Probabilidades invalidas')
        return p
    def classificar(self,mes,dia_semana,tipo_local,bairro):
        r=dict(mes=mes,dia_semana=dia_semana,tipo_local=tipo_local,bairro=bairro)
        # A mesma normalizacao do objeto treinado valida tipos, dominios e campos.
        raw=self.preprocessor._raw(r);warnings=[]
        for j,field in enumerate(FEATURES):
            value=raw[j]
            if value==MISSING:
                warnings.append({'campo':field,'codigo':'ausente','mensagem':'Valor ausente tratado pela categoria prevista no treinamento.'})
                if self.preprocessor.counts[field].get(MISSING,0)==0:
                    warnings.append({'campo':field,'codigo':'ausencia_sem_exemplos_treino','mensagem':'Esta ausencia e aceita tecnicamente, mas nao teve exemplos no treinamento.'})
                if field=='bairro' and isinstance(bairro,str) and any(c.isdigit() for c in bairro) and not any(c.isalpha() for c in bairro):
                    warnings.append({'campo':field,'codigo':'bairro_sem_nome','mensagem':'Texto sem nome de bairro foi convertido em ausente pela regra do preprocessador.'})
            elif field=='bairro' and value not in self.preprocessor.frequent:
                known=value in self.preprocessor.known[field]
                warnings.append({'campo':field,'codigo':'bairro_raro' if known else 'bairro_desconhecido','mensagem':'Bairro representado pelo agrupamento estatistico de baixa frequencia; a resposta pode ser limitada.'})
            elif field=='tipo_local' and value not in self.preprocessor.known[field]:
                warnings.append({'campo':field,'codigo':'local_desconhecido','mensagem':'Tipo de local desconhecido representado como ausente, conforme o preprocessador congelado.'})
        p=float(self.probabilities([r])[0]);label=int(p>=self.manifest['threshold'])
        return {'classe_estimada':'ROUBO' if label else 'FURTO','codigo_classe':label,'probabilidade_furto':1-p,'probabilidade_roubo':p,
          'versao_modelo':self.manifest['model_id'],'probabilidades_calibradas':self.calibrator is not None,'avisos':warnings}
