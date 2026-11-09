"""One-Hot esparso com vocabulario e frequencias aprendidos somente em 2023."""
from ml.runtime import FEATURES
import collections
import hashlib
import json
import unicodedata
import numbers
import numpy as np
from sklearn.preprocessing import OneHotEncoder

MISSING='__AUSENTE__'
UNKNOWN='__DESCONHECIDO__'
RARE='__BAIRRO_RARO__'
# Somente equivalencias de acentuacao inspecionadas em 2023; sem fuzzy matching
# nem equivalencia entre nomes abreviados, zonas diferentes ou bairros distintos.
ACCENT_ALIASES={
 'REPÚBLICA':'REPUBLICA','CONSOLAÇÃO':'CONSOLACAO','BRÁS':'BRAS','SÉ':'SE',
 'SACOMÃ':'SACOMA','FREGUESIA DO Ó':'FREGUESIA DO O','VILA JACUÍ':'VILA JACUI',
 'VILA OLÍMPIA':'VILA OLIMPIA','SÃO MATEUS':'SAO MATEUS','VILA SÔNIA':'VILA SONIA',
 'CAPÃO REDONDO':'CAPAO REDONDO','GRAJAÚ':'GRAJAU','ÁGUA RASA':'AGUA RASA',
 'CIDADE LÍDER':'CIDADE LIDER','JAGUARÁ':'JAGUARA','SÃO RAFAEL':'SAO RAFAEL'}

def digest_keys(keys):return hashlib.sha256('\n'.join(keys).encode()).hexdigest()
def normalized(value):
    if value is None:return MISSING
    if not isinstance(value,str):raise TypeError('Categoria nominal deve ser texto ou None')
    value=' '.join(unicodedata.normalize('NFC',value).strip().upper().split())
    if value in ('','NULL','NAN','N/A'):return MISSING
    if value.startswith('__'):raise ValueError('Categorias reservadas nao sao entradas publicas')
    return value

class Preprocessador:
    def __init__(self,min_bairro_count=50):
        if not isinstance(min_bairro_count,int) or min_bairro_count<1:raise ValueError('Limiar de raridade invalido')
        self.min_bairro_count=min_bairro_count

    def _normalize(self,record):
        if set(record)!=set(FEATURES):raise ValueError(f'Entradas devem conter exatamente {FEATURES}')
        values=[]
        for col,low,high in [('mes',1,12),('dia_semana',0,6)]:
            v=record[col]
            if v is None:values.append(MISSING)
            elif isinstance(v,numbers.Integral) and not isinstance(v,bool) and low<=v<=high:values.append(str(int(v)))
            else:raise ValueError(f'{col}: inteiro esperado entre {low} e {high}, ou None')
        local=normalized(record['tipo_local']); bairro=normalized(record['bairro'])
        if bairro!=MISSING and not any(ch.isalpha() for ch in bairro):bairro=MISSING
        bairro=self.aliases_.get(bairro,bairro) if hasattr(self,'aliases_') else bairro
        return values+[local,bairro]

    def fit(self,records,*,ano,chaves):
        if ano!=2023:raise ValueError('Ajuste permitido exclusivamente no treinamento de 2023')
        if len(records)!=len(chaves) or len(set(chaves))!=len(chaves):raise ValueError('Chaves ausentes, repetidas ou desalinhadas')
        raw=collections.Counter(normalized(r['bairro']) for r in records)
        # Alias so e ativado se as duas grafias foram realmente vistas no treino.
        self.aliases_={a:b for a,b in ACCENT_ALIASES.items() if a in raw and b in raw}
        data=np.asarray([self._normalize(r) for r in records],dtype=object)
        self.bairro_counts_=dict(collections.Counter(data[:,3]))
        self.frequent_bairros_=set(k for k,n in self.bairro_counts_.items() if k!=MISSING and n>=self.min_bairro_count)
        self.known_bairros_=set(self.bairro_counts_)-{MISSING}
        self.known_locais_=set(data[:,2])-{MISSING}
        categories=[sorted(set(data[:,j])|{MISSING},key=str) for j in range(4)]
        categories[3]=sorted(self.frequent_bairros_|{MISSING,RARE})
        mapped=self._map(data)
        self.encoder_=OneHotEncoder(categories=categories,handle_unknown='error',sparse_output=True,dtype=np.float32)
        self.encoder_.fit(mapped)
        self.feature_names_=self.encoder_.get_feature_names_out(FEATURES).tolist()
        self.fit_year_=ano;self.fit_rows_=len(records);self.fit_keys_sha256_=digest_keys(chaves)
        self.fit_records_sha256_=hashlib.sha256(json.dumps(records,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        self.train_stats_=self.diagnostics(records)
        return self

    def _map(self,data):
        out=data.copy()
        for j in [0,1]:
            # Validacao numerica limita meses/dias; categorias nao observadas usam UNKNOWN.
            if hasattr(self,'encoder_'):
                known=set(self.encoder_.categories_[j]);out[:,j]=[v if v in known else MISSING for v in out[:,j]]
        out[:,2]=[v if v==MISSING or v in self.known_locais_ else MISSING for v in out[:,2]]
        out[:,3]=[v if v==MISSING or v in self.frequent_bairros_ else RARE for v in out[:,3]]
        return out

    def transform(self,records):
        if not hasattr(self,'encoder_'):raise ValueError('Preprocessador nao ajustado')
        if not records:return self.encoder_.transform(np.empty((0,4),dtype=object))
        data=np.asarray([self._normalize(r) for r in records],dtype=object)
        return self.encoder_.transform(self._map(data)).tocsr()

    def diagnostics(self,records):
        data=np.asarray([self._normalize(r) for r in records],dtype=object);mapped=self._map(data)
        stats={'rows':len(records),'dimensao':sum(len(x) for x in self.encoder_.categories_),
               'bairros_observados_treino':len(self.known_bairros_),'bairros_retidos':len(self.frequent_bairros_),
               'aliases_ativados':self.aliases_,'limiar_bairro':self.min_bairro_count}
        for j,col in enumerate(FEATURES):
            known=self.known_locais_ if j==2 else self.known_bairros_ if j==3 else set(self.encoder_.categories_[j])
            stats[col]={'ausentes_entrada':int(sum(data[:,j]==MISSING)),
                        'desconhecidos':int(sum(v!=MISSING and v not in known for v in data[:,j])),
                        'raros':int(sum(mapped[:,j]==RARE))}
        return stats
