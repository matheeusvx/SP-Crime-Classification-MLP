"""Validacao de alinhamento completa; carregamento preditivo limitado a 2023/24."""
from ml.runtime import ROOT,OUT,FEATURES,json_write
import json
import duckdb
import numpy as np
import pyarrow.parquet as pq

EXPECTED={2023:190124,2024:158895,2025:156168}

def connection():
    c=duckdb.connect();c.execute("SET memory_limit='1500MB'");c.execute('SET threads=2')
    for name,file in [('base','base_modelagem'),('meta','metadados_modelagem'),('analytic','ocorrencias_elegiveis')]:
        p=(ROOT/f'data/processed/{file}.parquet').as_posix()
        c.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{p}')")
    c.execute('CREATE VIEW indexed AS SELECT row_number() OVER()-1 indice_linha,* FROM base')
    return c

def validate(c,write=False):
    def scalar(sql):return c.execute(sql).fetchall()[0][0]
    schema=json.loads((ROOT/'data/processed/esquema_modelagem.json').read_text(encoding='utf-8'))
    actual={r[0]:r[1] for r in c.execute('DESCRIBE base').fetchall()}
    expected={'mes':'TINYINT','dia_semana':'TINYINT','periodo_fato':'VARCHAR','tipo_local':'VARCHAR','bairro':'VARCHAR','alvo':'TINYINT'}
    if actual!=expected or schema['labels']!={'0':'FURTO','1':'ROUBO'}:raise ValueError('Esquema/rotulos da Etapa 1 divergentes')
    counts=dict(c.execute('SELECT ano_fato,count(*) FROM meta GROUP BY 1').fetchall())
    if counts!=EXPECTED:raise ValueError(f'Distribuicao temporal inesperada: {counts}')
    n=sum(counts.values())
    checks={
      'linhas_base':scalar('SELECT count(*) FROM base')==n,
      'linhas_analiticas':scalar('SELECT count(*) FROM analytic')==n,
      'indice_unico_contiguo':scalar('SELECT count(DISTINCT indice_linha)=count(*) AND min(indice_linha)=0 AND max(indice_linha)=count(*)-1 FROM meta'),
      'chaves_unicas':scalar('SELECT count(*)=count(DISTINCT chave_bo) AND count(chave_bo)=count(*) FROM meta'),
      'chaves_analiticas_unicas':scalar('SELECT count(*)=count(DISTINCT chave_bo) FROM analytic'),
      'sem_chaves_ausentes':scalar('SELECT count(*) FROM meta ANTI JOIN analytic USING(chave_bo)')==0,
      'alinhamento_celula_a_celula':scalar('''SELECT count(*) FROM indexed b JOIN meta m USING(indice_linha) JOIN analytic a USING(chave_bo)
       WHERE b.mes IS DISTINCT FROM a.mes OR b.dia_semana IS DISTINCT FROM a.dia_semana
       OR b.tipo_local IS DISTINCT FROM a.tipo_local OR b.bairro IS DISTINCT FROM a.bairro
       OR b.periodo_fato IS DISTINCT FROM a.periodo_fato OR b.alvo IS DISTINCT FROM a.alvo
       OR m.data_fato IS DISTINCT FROM a.data_fato OR m.ano_fato IS DISTINCT FROM year(m.data_fato)
       OR b.mes IS DISTINCT FROM month(m.data_fato) OR b.dia_semana IS DISTINCT FROM isodow(m.data_fato)-1''')==0,
      'rotulos_binarios':scalar('SELECT count(*) FROM base WHERE alvo IS NULL OR alvo NOT IN (0,1)')==0,
      'intervalos':scalar('SELECT count(*) FROM base WHERE mes IS NULL OR mes NOT BETWEEN 1 AND 12 OR dia_semana IS NULL OR dia_semana NOT BETWEEN 0 AND 6')==0,
      'grupos_sem_sobreposicao':scalar('SELECT count(*) FROM (SELECT chave_bo FROM meta GROUP BY 1 HAVING count(DISTINCT ano_fato)>1)')==0}
    if not all(checks.values()):raise ValueError(f'Integridade/alinhamento falhou: {checks}')
    # Igualdade de X ou (X,y) em BOs diferentes nao autoriza remover observacoes.
    duplicate=[]
    for year in [2023,2024]:
        x=c.execute(f'''SELECT count(*),sum(n-1),sum(CASE WHEN classes>1 THEN 1 ELSE 0 END) FROM
          (SELECT mes,dia_semana,tipo_local,bairro,count(*) n,count(DISTINCT alvo) classes
           FROM indexed JOIN meta USING(indice_linha) WHERE ano_fato={year} GROUP BY 1,2,3,4)''').fetchall()[0]
        duplicate.append({'ano':year,'tuplas_X_distintas':x[0],'repeticoes_X_entre_BOs':x[1],'tuplas_X_com_ambas_classes':x[2]})
    out={'counts':counts,'checks':checks,'schema':actual,'duplicidade_contextos':duplicate,
       'test_2025':'somente integridade, contagem e alinhamento; sem transformacao ou inferencia',
       'alignment':'indice_linha + chave_bo + comparacao de todos os campos com a base analitica independente'}
    if write:json_write(OUT/'validacao_dados.json',out)
    return out

def load_year(c,year):
    if year not in (2023,2024):raise ValueError('2025 isolado: carregamento preditivo proibido nesta etapa')
    cols=','.join('b.'+x for x in FEATURES)
    t=c.sql(f'''SELECT {cols},b.alvo,m.chave_bo FROM indexed b JOIN meta m USING(indice_linha)
          WHERE year(m.data_fato)={int(year)} ORDER BY m.indice_linha''').to_arrow_table()
    records=[{k:row[k] for k in FEATURES} for row in t.select(FEATURES).to_pylist()]
    return records,np.asarray(t['alvo'].to_numpy(),dtype=np.int8),t['chave_bo'].to_pylist()

def structural_inspection():
    c=connection();v=validate(c,True)
    train,y,keys=load_year(c,2023)
    import re,unicodedata,collections
    categories={};suspicious=[];variants={}
    for col in FEATURES:
        counter=collections.Counter(r[col] for r in train)
        categories[col]=[{'categoria':k,'n':n} for k,n in counter.most_common()]
        for value,n in counter.items():
            if isinstance(value,str):
                canonical=''.join(ch for ch in unicodedata.normalize('NFKD',value) if not unicodedata.combining(ch))
                if re.search(r'FURT|ROUB|LATROC|SUBTRA|ART\.?\s*15[57]',canonical):suspicious.append({'campo':col,'categoria':value,'n':n})
        if col=='bairro':
            buckets=collections.defaultdict(list)
            for value,n in counter.items():
                if value is not None:
                    k=''.join(ch for ch in unicodedata.normalize('NFKD',value) if not unicodedata.combining(ch))
                    buckets[k].append({'grafia':value,'n':n})
            variants={k:v for k,v in buckets.items() if len(v)>1}
    json_write(OUT/'categorias_treino.json',{'ano_fit':2023,'categorias':categories,'possiveis_equivalencias_acento':variants,'suspeitas_semanticas':suspicious})
    print(json.dumps({'validacao':v,'cardinalidades_treino':{k:len(v) for k,v in categories.items()},'suspeitas':suspicious,'variantes_acento':list(variants.items())[:20]},ensure_ascii=False,indent=2))

if __name__=='__main__':structural_inspection()
