"""Pre-processamento experimental independente; calendario e subconjuntos explicitos."""
from experiments4.common import FEATURES
from ml.preprocessing import normalized,ACCENT_ALIASES,MISSING,RARE,digest_keys
import collections,hashlib,json,numbers,unicodedata
import numpy as np
from sklearn.preprocessing import OneHotEncoder

def accent_key(s):return ''.join(c for c in unicodedata.normalize('NFD',s) if not unicodedata.combining(c))

class ExperimentalPreprocessor:
    def __init__(self,features,min_count=50,local_alias=False):
        if not features or len(set(features))!=len(features) or not set(features)<=set(FEATURES):raise ValueError('Atributos nao autorizados')
        if min_count not in (10,50,100):raise ValueError('Limiar fora da matriz planejada')
        self.features=list(features);self.min_count=min_count;self.local_alias=local_alias
    def _raw(self,r):
        if set(r)!=set(self.features):raise ValueError('Esquema de inferencia difere das entradas autorizadas')
        out=[]
        for f in self.features:
            v=r[f]
            if f in ['mes','dia_semana']:
                lo,hi=(1,12) if f=='mes' else (0,6)
                if v is None:v=MISSING
                elif isinstance(v,numbers.Integral) and not isinstance(v,bool) and lo<=v<=hi:v=str(int(v))
                else:raise ValueError(f'{f}: inteiro invalido')
            else:
                v=normalized(v)
                if f=='bairro':
                    if v!=MISSING and not any(c.isalpha() for c in v):v=MISSING
                    v=getattr(self,'aliases',{}).get(v,v)
                elif f=='tipo_local' and self.local_alias and v!=MISSING:v=getattr(self,'local_map',{}).get(accent_key(v),v)
            out.append(v)
        return out
    def fit(self,records,*,scope,keys,months):
        if scope not in ['interno_2023_JanSet','completo_2023']:raise ValueError('Escopo de ajuste proibido')
        if len(records)!=len(keys) or len(keys)!=len(set(keys)):raise ValueError('Chaves invalidas')
        if len(months)!=len(records) or not all(1<=m<=(9 if scope=='interno_2023_JanSet' else 12) for m in months):raise ValueError('Dados fora do periodo de ajuste')
        self.aliases={};self.local_map={}
        if 'bairro' in self.features:
            names={normalized(r['bairro']) for r in records};self.aliases={a:b for a,b in ACCENT_ALIASES.items() if a in names and b in names}
        if 'tipo_local' in self.features and self.local_alias:
            for value in {normalized(r['tipo_local']) for r in records}-{MISSING}:
                k=accent_key(value)
                if k in self.local_map and self.local_map[k]!=value:raise ValueError('Colisao de nomes: semantica incerta')
                self.local_map[k]=value
        raw=np.asarray([self._raw(r) for r in records],dtype=object)
        self.known={f:set(raw[:,j])-{MISSING} for j,f in enumerate(self.features)}
        self.counts={f:dict(collections.Counter(raw[:,j])) for j,f in enumerate(self.features)}
        self.frequent={k for k,n in self.counts.get('bairro',{}).items() if k!=MISSING and n>=self.min_count}
        categories=[]
        for j,f in enumerate(self.features):
            if f=='mes':levels={str(i) for i in range(1,13)}|{MISSING}
            elif f=='dia_semana':levels={str(i) for i in range(7)}|{MISSING}
            elif f=='bairro':levels=self.frequent|{MISSING,RARE}
            else:levels=self.known[f]|{MISSING}
            categories.append(sorted(levels))
        self.encoder=OneHotEncoder(categories=categories,handle_unknown='error',sparse_output=True,dtype=np.float32)
        self.encoder.fit(self._map(raw));self.names=self.encoder.get_feature_names_out(self.features).tolist()
        self.scope=scope;self.rows=len(records);self.fit_keys_hash=digest_keys(keys)
        self.fit_records_hash=hashlib.sha256(json.dumps(records,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        self.months=sorted(set(months));self.stats=self.describe(records)
        return self
    def _map(self,raw):
        out=raw.copy()
        for j,f in enumerate(self.features):
            if f=='bairro':out[:,j]=[v if v==MISSING or v in self.frequent else RARE for v in raw[:,j]]
            elif f=='tipo_local':out[:,j]=[v if v==MISSING or v in self.known[f] else MISSING for v in raw[:,j]]
        return out
    def transform(self,records):
        return self.encoder.transform(self._map(np.asarray([self._raw(r) for r in records],dtype=object))).tocsr()
    def describe(self,records):
        raw=np.asarray([self._raw(r) for r in records],dtype=object)
        result={'rows':len(records),'dimension':len(self.names),'retained_bairros':len(self.frequent),'min_count':self.min_count}
        for j,f in enumerate(self.features):
            result[f]={'missing':int(sum(raw[:,j]==MISSING)),'unknown':int(sum(v!=MISSING and v not in self.known[f] for v in raw[:,j])),
                       'rare_bucket':int(sum(v!=MISSING and v not in self.frequent for v in raw[:,j])) if f=='bairro' else 0}
        return result
