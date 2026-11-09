"""Auditoria anterior ao recorte e rotulagem; apenas agregados em reports."""
import time
import sys
import platform
import importlib.metadata
from common import *

FREQUENCIES=['RUBRICA','FLAG_STATUS','DESC_LEI','DESCR_CONDUTA','DESDOBRAMENTO','CIRCUNSTANCIA',
             'DESCR_PERIODO','DESCR_TIPOLOCAL','DESCR_SUBTIPOLOCAL','DESCR_MODO_OBJETO',
             'DESCR_TIPO_OBJETO','DESCR_SUBTIPO_OBJETO','NOME_MUNICIPIO_CIRC']

def audit():
    start=time.perf_counter(); con=connect(); raw_view(con); profiles=[]
    inventory=[]
    for year in (2023,2024,2025):
        manifest=json.loads((ROOT/f'data/interim/{year}.json').read_text(encoding='utf-8')); inventory.append(manifest)
        table=f"read_parquet('{(ROOT/f'data/interim/{year}.parquet').as_posix()}')"
        for col in manifest['columns']:
            v=clean(q(col))
            r=con.execute(f'''SELECT count(*),count(*)-count({v}),count(DISTINCT {v}),
                count(try_cast({v} AS DOUBLE)),count(*) FILTER(WHERE {q(col)} IS NOT NULL AND {v} IS NULL),
                count(*) FILTER(WHERE {q(col)} IS NOT NULL AND trim({q(col)})!={q(col)}),
                count(*) FILTER(WHERE {v} IS NOT NULL AND upper({v})!={v})
                FROM {table}''').fetchone()
            n,missing,card,numeric,sentinels,trimmed,uppercase=r
            dtype='serial_excel' if col.startswith('DATA') else ('fracao_dia_ou_texto' if col=='HORA_OCORRENCIA' else ('numerico_lexical' if numeric==n-missing and numeric else 'texto'))
            profiles.append({'ano_arquivo':year,'original':col,'padronizada':col.lower(),'linhas':n,'ausentes':missing,'ausentes_pct':round(100*missing/n,4),'distintos_nao_nulos':card,'tipo_observado':dtype,'numericos_parseaveis':numeric,'marcadores_ausencia':sentinels,'linhas_trim_alteraria':trimmed,'linhas_maiusculas_alteraria':uppercase})
        print(f'{year}: perfis de {len(manifest["columns"])} colunas concluidos',flush=True)
    with (ROOT/'reports/tables/perfil_colunas.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(profiles[0])); w.writeheader(); w.writerows(profiles)
    write_json(Path('reports/inventario.json'),inventory)
    for col in FREQUENCIES:
        save_table(con,f'SELECT _source_year ano_arquivo,{clean(q(col))} valor,count(*) linhas FROM raw GROUP BY ALL ORDER BY 1,3 DESC','frequencia_'+col.lower())
    save_table(con,f'''SELECT _source_year ano_arquivo,{clean('NOME_MUNICIPIO_CIRC')} municipio_circ,
      {clean('CIDADE')} cidade,{clean('CD_IBGE')} ibge,count(*) linhas FROM raw GROUP BY ALL ORDER BY 1,5 DESC''','geografia_cruzada')
    # Datas guardadas como lexemas; conversao explicita do sistema Excel 1900.
    for col in ['DATA_OCORRENCIA_BO','DATAHORA_REGISTRO_BO','DATA_COMUNICACAO_BO']:
        v=clean(q(col)); serial=f'try_cast({v} AS DOUBLE)'
        d=f"CASE WHEN {serial} BETWEEN 1 AND 100000 THEN DATE '1899-12-30' + cast(floor({serial}) AS INTEGER) END"
        save_table(con,f'''SELECT _source_year ano_arquivo,min({d}) menor,max({d}) maior,
          count(*) FILTER(WHERE {v} IS NOT NULL AND {d} IS NULL) invalidas,
          count(*) FILTER(WHERE {v} IS NULL) ausentes,
          count(*) FILTER(WHERE year({d})!=_source_year) fora_ano_arquivo FROM raw GROUP BY 1''','datas_'+col.lower())
        save_table(con,f"SELECT _source_year ano_arquivo,strftime({d},'%Y-%m') mes_fato,count(*) linhas FROM raw GROUP BY ALL ORDER BY 1,2",'mensal_'+col.lower())
    save_table(con,'''SELECT _source_year ano_arquivo,
        count(*) FILTER(WHERE try_cast(DATAHORA_REGISTRO_BO AS DOUBLE)<try_cast(DATA_OCORRENCIA_BO AS DOUBLE)) registro_anterior_fato,
        avg(try_cast(DATAHORA_REGISTRO_BO AS DOUBLE)-try_cast(DATA_OCORRENCIA_BO AS DOUBLE)) atraso_medio_dias,
        median(try_cast(DATAHORA_REGISTRO_BO AS DOUBLE)-try_cast(DATA_OCORRENCIA_BO AS DOUBLE)) atraso_mediano_dias
        FROM raw GROUP BY 1''','atraso_registro')
    save_table(con,'''SELECT _source_year ano_arquivo,HORA_OCORRENCIA valor,count(*) linhas FROM raw
       WHERE HORA_OCORRENCIA IS NOT NULL AND upper(trim(HORA_OCORRENCIA))!='NULL'
       GROUP BY ALL ORDER BY 1,3 DESC LIMIT 100''','horas_auditoria')
    write_json(Path('reports/auditoria_execucao.json'),{'seconds':round(time.perf_counter()-start,2)})
    import psutil
    write_json(Path('reports/ambiente.json'),{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
        'dependencies':{m:importlib.metadata.version(m) for m in ['pyarrow','duckdb','matplotlib','psutil']},
        'ram_total_gib':round(psutil.virtual_memory().total/1024**3,2),'duckdb_memory_limit':'1500MB','threads':2})
    print('Auditoria original concluida; consulte reports/tables.',flush=True)

if __name__=='__main__':
    (ROOT/'reports/tables').mkdir(parents=True,exist_ok=True); audit()
