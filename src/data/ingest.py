"""Leitura incremental OOXML; preserva lexemas originais em Parquet local."""
import argparse
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.runtime'))
sys.path.insert(0,str(ROOT))
import pyarrow as pa
import pyarrow.parquet as pq
import psutil
from ooxml import rows, strings, NS, ET

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def ingest(path,year,force=False):
    start=time.perf_counter(); checksum=digest(path)
    dest=ROOT/f'data/interim/{year}.parquet'; manifest=dest.with_suffix('.json')
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not force and manifest.exists() and dest.exists():
        m=json.loads(manifest.read_text(encoding='utf-8'))
        if m['sha256']==checksum and m.get('parser_version')==1:
            print(f'{year}: cache validado por SHA256',flush=True); return
    with zipfile.ZipFile(path) as z:
        ss=strings(z)
        book=ET.fromstring(z.read('xl/workbook.xml'))
        properties=book.find(NS+'workbookPr')
        if properties is not None and properties.get('date1904') in ('1','true'):
            raise ValueError('Calendario Excel 1904 exige conversao especifica; interrompido sem alterar datas')
        sheets=[s.get('name') for s in book.find(NS+'sheets')]
        # Resolve os alvos reais via relacionamentos do workbook, sem assumir sheet3.
        rel=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        targets={r.get('Id'):r.get('Target') for r in rel}
        sheetmeta=[]; selected=None
        for s in book.find(NS+'sheets'):
            target=targets[s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            member=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            it=rows(z,member,ss); head=next(it,(None,[]))[1]
            sheetmeta.append({'name':s.get('name'),'member':member})
            if 'RUBRICA' in head and 'NUM_BO' in head:
                if selected: raise ValueError('Mais de uma aba de dados: revisar descoberta')
                selected=(s.get('name'),member,head)
        if not selected: raise ValueError('Aba de dados nao identificada')
        sheet,member,headers=selected
        if len(set(headers))!=len(headers): raise ValueError('Cabecalhos duplicados')
        schema=pa.schema([(str(c),pa.string()) for c in headers]+[('_source_year',pa.int16()),('_source_row',pa.int32())])
        tmp=dest.with_suffix('.partial.parquet'); batch=[]; n=0; blanks=0; peak=0
        with pq.ParquetWriter(tmp,schema,compression='zstd') as writer:
            for lineno,values in rows(z,member,ss):
                if lineno==1: continue
                if not any(v is not None for v in values): blanks+=1; continue
                if len(values)>len(headers): raise ValueError(f'Linha {lineno} excede esquema')
                values=values+[None]*(len(headers)-len(values))
                batch.append(dict(zip(headers,values))|{'_source_year':year,'_source_row':lineno}); n+=1
                if len(batch)>=20000:
                    writer.write_table(pa.Table.from_pylist(batch,schema=schema)); batch.clear()
                    peak=max(peak,psutil.Process().memory_info().rss)
                    if n%100000==0: print(f'{year}: {n:,} linhas lidas',flush=True)
            if batch: writer.write_table(pa.Table.from_pylist(batch,schema=schema))
        tmp.replace(dest)
    if digest(path)!=checksum: raise RuntimeError('Original mudou durante leitura')
    m={'parser_version':1,'path':str(path),'year':year,'bytes':path.stat().st_size,'format':'XLSX/OOXML ZIP',
       'sha256':checksum,'sheets':sheetmeta,'data_sheet':sheet,'columns':headers,'rows':n,'blank_rows':blanks,
       'seconds':round(time.perf_counter()-start,2),'rss_peak_sampled_mb':round(peak/1024**2,1),
       'storage':'Lexemas XML preservados como string; datas seriais Excel convertidas apenas na preparacao.'}
    manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{year}: concluido, {n:,} linhas; {m["seconds"]} s',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input-dir',type=Path,default=Path('D:/')); p.add_argument('--force',action='store_true'); a=p.parse_args()
    for year in (2023,2024,2025): ingest(a.input_dir/f'CelularesSubtraidos_{year}.xlsx',year,a.force)
