"""Recorte conservador e consolidacao por boletim, sem ajuste de estimadores."""
from common import *

FEATURES=['mes','dia_semana','periodo_fato','tipo_local','bairro']
LABELS={'FURTO (ART. 155)':0,'ROUBO (ART. 157)':1}

def copy(con,query,name):
    path=ROOT/'data/processed'/name
    con.execute(f"COPY ({query}) TO '{path.as_posix()}' (FORMAT PARQUET,COMPRESSION ZSTD)")

def prepare():
    con=connect(); raw_view(con); (ROOT/'data/processed').mkdir(parents=True,exist_ok=True)
    cols=[r[0] for r in con.execute('DESCRIBE raw').fetchall()]
    normalized=[f'{clean(q(c))} AS {q(c)}' for c in cols if not c.startswith('_')]
    con.execute('CREATE VIEW normalized AS SELECT '+','.join(normalized)+',_source_year,_source_row FROM raw')
    date="CASE WHEN try_cast(DATA_OCORRENCIA_BO AS DOUBLE) BETWEEN 1 AND 100000 THEN DATE '1899-12-30'+cast(floor(try_cast(DATA_OCORRENCIA_BO AS DOUBLE)) AS INTEGER) END"
    key="CASE WHEN NOME_DELEGACIA IS NOT NULL AND ANO_BO IS NOT NULL AND NUM_BO IS NOT NULL THEN sha256(to_json(list_value(upper(NOME_DELEGACIA),ANO_BO,NUM_BO))) END"
    con.execute(f'''CREATE TABLE lines AS SELECT *,{key} chave_bo,{date} data_fato,
       CASE upper(RUBRICA) WHEN 'FURTO (ART. 155)' THEN 0 WHEN 'ROUBO (ART. 157)' THEN 1 END alvo,
       CASE WHEN NOME_MUNICIPIO_CIRC IS NULL THEN 'municipio_ausente'
            WHEN upper(NOME_MUNICIPIO_CIRC) NOT IN ('S.PAULO','SAO PAULO','SÃO PAULO') THEN 'outro_municipio'
            WHEN CD_IBGE IS NOT NULL AND CD_IBGE!='3550308' THEN 'conflito_ibge'
            ELSE 'capital' END geo,
       CASE WHEN try_cast(HORA_OCORRENCIA AS DOUBLE)>=0 AND try_cast(HORA_OCORRENCIA AS DOUBLE)<1
            THEN cast(floor(try_cast(HORA_OCORRENCIA AS DOUBLE)*24) AS INTEGER)
            WHEN regexp_full_match(HORA_OCORRENCIA,'[0-2][0-9]:[0-5][0-9](:[0-5][0-9])?')
                 AND try_cast(substr(HORA_OCORRENCIA,1,2) AS INTEGER)<24
            THEN try_cast(substr(HORA_OCORRENCIA,1,2) AS INTEGER) END hora_validada
       FROM normalized''')
    save_table(con,'''SELECT _source_year ano_arquivo,count(*) originais,
       count(*) FILTER(WHERE geo='capital') linhas_capital,
       count(*) FILTER(WHERE geo='municipio_ausente') municipio_indeterminado,
       count(*) FILTER(WHERE geo='outro_municipio') outros_municipios,
       count(*) FILTER(WHERE geo='conflito_ibge') conflitos_ibge,
       count(*) FILTER(WHERE chave_bo IS NULL) chave_incompleta,
       count(*) FILTER(WHERE HORA_OCORRENCIA IS NOT NULL AND hora_validada IS NULL) hora_invalida
       FROM lines GROUP BY 1 ORDER BY 1''','recorte_linhas')
    save_table(con,'''SELECT RUBRICA natureza,alvo,count(*) linhas,
       CASE WHEN alvo IS NULL THEN 'segregar: fora da definicao binaria explicita'
       ELSE 'aceitar por igualdade de rubrica; qualificadoras e tentativa mantidas' END decisao
       FROM lines GROUP BY ALL ORDER BY 3 DESC''','mapeamento_classes')
    save_table(con,'''SELECT _source_year ano_arquivo,RUBRICA,FLAG_STATUS,DESCR_CONDUTA,DESDOBRAMENTO,CIRCUNSTANCIA,count(*) linhas
       FROM lines WHERE alvo IS NOT NULL GROUP BY ALL ORDER BY 1,7 DESC''','qualificadoras_classes')
    # Hash de tupla identifica agrupamento, nao implica que cada linha seja duplicata.
    attrs=['hora_validada','DESCR_PERIODO','DESCR_TIPOLOCAL','BAIRRO']
    collapsed=[]
    for a in attrs:
        val=a if a=='hora_validada' else f'upper({a})'
        collapsed.extend([f'CASE WHEN count(DISTINCT {val})=1 THEN min({val}) END {q(a.lower())}',
                          f'count(DISTINCT {val}) {q("n_"+a.lower())}'])
    con.execute(f'''CREATE TABLE groups AS SELECT chave_bo,count(*) linhas_vinculadas,
       min(_source_year) primeiro_arquivo,max(_source_year) ultimo_arquivo,count(DISTINCT _source_year) n_arquivos,
       count(DISTINCT VERSAO) n_versoes,count(DISTINCT RUBRICA) n_naturezas,
       count(DISTINCT alvo) n_classes,min(alvo) alvo,
       count(*) FILTER(WHERE alvo IS NULL) linhas_sem_alvo,
       count(*) FILTER(WHERE geo!='capital') linhas_fora_capital,
       count(*) FILTER(WHERE geo='capital') linhas_capital,
       count(*) FILTER(WHERE data_fato IS NULL) datas_invalidas_ausentes,
       count(DISTINCT data_fato) n_datas,min(data_fato) data_fato,
       count(*) FILTER(WHERE data_fato NOT BETWEEN DATE '2023-01-01' AND DATE '2025-12-31') fora_periodo,
       {','.join(collapsed)} FROM lines WHERE chave_bo IS NOT NULL GROUP BY chave_bo''')
    con.execute('''CREATE TABLE decisions AS SELECT *,CASE
       WHEN linhas_fora_capital>0 THEN CASE WHEN linhas_capital>0 THEN 'geografia_conflitante' ELSE 'fora_capital_ou_indeterminado' END
       WHEN datas_invalidas_ausentes>0 THEN 'data_ausente_invalida'
       WHEN n_datas!=1 THEN 'datas_conflitantes'
       WHEN fora_periodo>0 THEN 'fato_fora_2023_2025'
       WHEN n_classes>1 THEN 'roubo_e_furto_no_bo'
       WHEN n_classes=0 THEN 'sem_classe_binaria'
       WHEN linhas_sem_alvo>0 THEN 'outras_naturezas_associadas'
       ELSE 'elegivel' END decisao FROM groups''')
    save_table(con,'''SELECT decisao,count(*) boletins,sum(linhas_vinculadas) linhas_origem,
       round(100.0*count(*)/sum(count(*)) OVER(),4) pct_boletins FROM decisions GROUP BY 1 ORDER BY 2 DESC''','decisoes_boletins')
    save_table(con,'''SELECT primeiro_arquivo ano_primeiro_arquivo,decisao,count(*) boletins,sum(linhas_vinculadas) linhas_origem
       FROM decisions GROUP BY ALL ORDER BY 1,2''','decisoes_por_arquivo')
    save_table(con,'''SELECT count(*) boletins,count(*) FILTER(WHERE linhas_vinculadas>1) multiplas_linhas,
       sum(linhas_vinculadas-1) linhas_acima_de_um_por_bo,
       count(*) FILTER(WHERE n_arquivos>1) em_multiplos_arquivos,
       count(*) FILTER(WHERE n_versoes>1) multiplas_versoes,
       count(*) FILTER(WHERE n_naturezas>1) multiplas_naturezas,
       count(*) FILTER(WHERE n_classes>1) classes_mistas,
       count(*) FILTER(WHERE n_datas>1) datas_conflitantes FROM groups''','granularidade')
    save_table(con,'''SELECT decisao,sum(CASE WHEN n_hora_validada>1 THEN 1 ELSE 0 END) conflito_hora,
       sum(CASE WHEN n_descr_periodo>1 THEN 1 ELSE 0 END) conflito_periodo,
       sum(CASE WHEN n_descr_tipolocal>1 THEN 1 ELSE 0 END) conflito_tipo_local,
       sum(CASE WHEN n_bairro>1 THEN 1 ELSE 0 END) conflito_bairro FROM decisions GROUP BY 1''','conflitos_atributos')
    # Identidade integral da linha original por ano, com igualdade de todos os campos.
    original=[q(c) for c in cols if not c.startswith('_')]
    save_table(con,f'''SELECT _source_year ano_arquivo,sum(n) linhas,count(*) linhas_distintas,sum(n-1) repeticoes_exatas
        FROM (SELECT _source_year,{','.join(original)},count(*) n FROM raw GROUP BY ALL)
        GROUP BY 1 ORDER BY 1''','duplicatas_exatas')
    con.execute('''CREATE TABLE eligible AS SELECT chave_bo,data_fato,year(data_fato)::SMALLINT ano_fato,
       month(data_fato)::TINYINT mes,(isodow(data_fato)-1)::TINYINT dia_semana,
       hora_validada::TINYINT hora,descr_periodo periodo,
       CASE WHEN hora_validada BETWEEN 0 AND 5 THEN 'MADRUGADA'
            WHEN hora_validada BETWEEN 6 AND 11 THEN 'MANHA'
            WHEN hora_validada BETWEEN 12 AND 17 THEN 'TARDE'
            WHEN hora_validada BETWEEN 18 AND 23 THEN 'NOITE'
            WHEN descr_periodo='DE MADRUGADA' THEN 'MADRUGADA'
            WHEN descr_periodo='PELA MANHÃ' THEN 'MANHA'
            WHEN descr_periodo='A TARDE' THEN 'TARDE'
            WHEN descr_periodo='A NOITE' THEN 'NOITE'
            WHEN descr_periodo='EM HORA INCERTA' THEN 'INCERTO' END periodo_fato,
       descr_tipolocal tipo_local,bairro,
       alvo::TINYINT alvo,'3550308' municipio_ibge,linhas_vinculadas,n_arquivos,primeiro_arquivo,ultimo_arquivo
       FROM decisions WHERE decisao='elegivel' ''')
    copy(con,'SELECT * FROM eligible ORDER BY chave_bo','ocorrencias_elegiveis.parquet')
    copy(con,'SELECT '+','.join(FEATURES)+',alvo FROM eligible ORDER BY chave_bo','base_modelagem.parquet')
    copy(con,'''SELECT row_number() OVER(ORDER BY chave_bo)-1 indice_linha,chave_bo,data_fato,ano_fato,municipio_ibge,
       primeiro_arquivo,ultimo_arquivo FROM eligible ORDER BY chave_bo''','metadados_modelagem.parquet')
    # Quarentena local tem apenas chave tecnica, motivos e contagens; nao revela endereco.
    copy(con,"SELECT chave_bo,decisao,linhas_vinculadas,n_classes,n_naturezas,n_datas,primeiro_arquivo,ultimo_arquivo FROM decisions WHERE decisao!='elegivel'",'quarentena_boletins.parquet')
    save_table(con,'''SELECT ano_fato,alvo,count(*) boletins,round(100.0*count(*)/sum(count(*)) OVER(PARTITION BY ano_fato),4) pct_ano
        FROM eligible GROUP BY ano_fato,alvo ORDER BY 1,2''','classes_por_ano')
    save_table(con,'''SELECT alvo,count(*) boletins,round(100.0*count(*)/sum(count(*)) OVER(),4) percentual
        FROM eligible GROUP BY 1 ORDER BY 1''','classes_total')
    save_table(con,"SELECT strftime(data_fato,'%Y-%m') mes_fato,alvo,count(*) boletins FROM eligible GROUP BY ALL ORDER BY 1,2",'classes_mensal')
    for col in ['periodo','periodo_fato','tipo_local','bairro']:
        save_table(con,f'SELECT {col},alvo,count(*) boletins FROM eligible GROUP BY ALL ORDER BY 3 DESC','distribuicao_'+col)
    attrprofile=[]
    for col in FEATURES:
        n,m,d=con.execute(f'SELECT count(*),count(*)-count({col}),count(DISTINCT {col}) FROM eligible').fetchone()
        attrprofile.append({'atributo':col,'linhas':n,'ausentes':m,'ausentes_pct':round(100*m/n,4) if n else None,'cardinalidade':d})
    write_json(Path('reports/perfil_atributos.json'),attrprofile)
    # Maior resto define cotas proporcionais, sem forcar equilibrio de classes.
    total=con.execute('SELECT count(*) FROM eligible').fetchone()[0]; size=min(20000,total)
    con.execute(f'''CREATE TABLE quotas AS WITH x AS (
       SELECT ano_fato,mes,alvo,count(*) n,count(*)*{size}.0/{max(total,1)} ideal FROM eligible GROUP BY ALL),
       y AS (SELECT *,floor(ideal)::INTEGER base,ideal-floor(ideal) resto FROM x),
       z AS (SELECT *,row_number() OVER(ORDER BY resto DESC,ano_fato,mes,alvo) ordem FROM y)
       SELECT *,base+CASE WHEN ordem<={size}-(SELECT sum(base) FROM y) THEN 1 ELSE 0 END cota FROM z''')
    con.execute('''CREATE TABLE sample AS SELECT e.* EXCLUDE (rn) FROM
       (SELECT *,row_number() OVER(PARTITION BY ano_fato,mes,alvo ORDER BY sha256('GS2026-semente42|'||chave_bo)) rn FROM eligible) e
       JOIN quotas q USING(ano_fato,mes,alvo) WHERE e.rn<=q.cota''')
    copy(con,'SELECT * FROM sample ORDER BY chave_bo','amostra_experimental_20000.parquet')
    save_table(con,'SELECT ano_fato,mes,alvo,n populacao,cota amostra FROM quotas ORDER BY 1,2,3','amostragem_cotas')
    write_json(Path('data/processed/esquema_modelagem.json'),{'features':FEATURES,'target':'alvo','labels':{'0':'FURTO','1':'ROUBO'},'metadata':'metadados_modelagem.parquet','alignment':'mesma ordenacao por chave_bo; indice_linha zero-based','rows':total,'sample_rows':size,'split':'nao realizado','fitted_transformers':False})
    print(f'Preparacao concluida: {total:,} boletins elegiveis; amostra {size:,}.',flush=True)

if __name__=='__main__': prepare()
