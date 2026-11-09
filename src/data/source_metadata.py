"""Extrai somente a documentacao das abas de apoio, em cada execucao."""
import zipfile
from common import *
from ooxml import rows,strings,NS,ET

def extract_support(input_dir):
    out=[]
    for year in (2023,2024,2025):
        with zipfile.ZipFile(input_dir/f'CelularesSubtraidos_{year}.xlsx') as z:
            ss=strings(z); book=ET.fromstring(z.read('xl/workbook.xml'))
            rel={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
            info={'year':year,'support':{},'headers':None}
            for s in book.find(NS+'sheets'):
                target=rel[s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
                member=target.lstrip('/') if target.startswith('/') else 'xl/'+target
                it=rows(z,member,ss); first=next(it,(None,[]))
                if 'RUBRICA' in first[1] and 'NUM_BO' in first[1]:info['headers']=first[1]
                else:
                    data=[first]+list(it)
                    key='dictionary' if any(v and v[0]=='Campos' for _,v in data) else 'methodology'
                    info['support'][key]=[(n,v) for n,v in data if any(v)]
            out.append(info)
    write_json(Path('reports/documentacao_fonte.json'),out)
