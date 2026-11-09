import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.runtime'))
import duckdb

def connect():
    con=duckdb.connect()
    con.execute("SET memory_limit='1500MB'")
    con.execute('SET threads=2')
    con.execute(f"SET temp_directory='{(ROOT/'data/interim/tmp').as_posix()}'")
    return con

def save_table(con,sql,name):
    cur=con.execute(sql); columns=[x[0] for x in cur.description]; rows=cur.fetchall()
    p=ROOT/'reports/tables'/f'{name}.csv'; p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(columns); w.writerows(rows)
    return [dict(zip(columns,row)) for row in rows]

def q(name): return '"'+name.replace('"','""')+'"'
def clean(expr): return f"CASE WHEN upper(trim({expr})) IN ('','NULL','N/A','NAN') THEN NULL ELSE trim({expr}) END"
def raw_view(con):
    glob=(ROOT/'data/interim/202*.parquet').as_posix()
    con.execute(f"CREATE VIEW raw AS SELECT * FROM read_parquet('{glob}',union_by_name=true)")

def write_json(path,value):
    path=ROOT/path; path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
