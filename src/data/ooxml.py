import json, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
def strings(z):
    if 'xl/sharedStrings.xml' not in z.namelist(): return []
    out=[]
    for _,e in ET.iterparse(z.open('xl/sharedStrings.xml'),events=('end',)):
        if e.tag==NS+'si':
            out.append(''.join(t.text or '' for t in e.iter(NS+'t'))); e.clear()
    return out
def rows(z, sheet, ss):
    with z.open(sheet) as f:
        for _,e in ET.iterparse(f,events=('end',)):
            if e.tag!=NS+'row': continue
            vals=[]
            for c in e:
                ref=c.get('r','A1'); letters=''.join(x for x in ref if x.isalpha()); idx=0
                for x in letters: idx=idx*26+ord(x)-64
                while len(vals)<idx: vals.append(None)
                v=c.find(NS+'v'); v=v.text if v is not None else None
                if c.get('t')=='s' and v is not None: v=ss[int(v)]
                elif c.get('t')=='inlineStr': v=''.join(t.text or '' for t in c.iter(NS+'t'))
                vals[idx-1]=v
            yield int(e.get('r')),vals
            e.clear()
