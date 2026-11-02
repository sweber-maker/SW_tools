"""v4.2 to v3.1 converter: retain template XML rather than rebuilding Excel styling."""
from pathlib import Path
from copy import deepcopy
import argparse, csv, difflib, io, json, re, zipfile
from lxml import etree as ET
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

VERSION = '1.02'
TEMPLATE = Path(__file__).parent / 'templates/v3.1.xlsx'
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
Q = lambda name: f'{{{NS}}}{name}'
MAP = {'A':'A', 'B':'B', 'C':'C', **{get_column_letter(i):get_column_letter(i-3) for i in range(7,23)}}
GROUPS = {'D':'Isotype','E':'Light Chain (λ or κ)','G':'VH Vector Name - Insertion Site Name','H':'Kozak Setting','I':'Kozak Sequence','J':'Leader Setting','K':'Leader Sequence','N':'VL Vector Name - Insertion Site Name','O':'Kozak Setting','P':'Kozak Sequence','Q':'Leader Setting','R':'Leader Sequence'}
ORDER_CATEGORIES = {3:'Scale*',4:'Pooling',5:'Cell Line',6:'Purification',7:'Elution Buffer*',8:'Buffer Exchange',9:'Normatlization',10:'Post Purification Sterile Filtration',11:'Aliquots',12:'Shipping Container*',13:'Custom Plate Map',14:'Restriction Enzyme Sites to Avoid for DNA Optimization',15:'Please indicate if you prefer not to receive physical samples and only data',16:'Ship with testing pending'}
ALIASES = {3:['scale','production scale','expression scale'],4:['pooling'],5:['cell line','expression host'],6:['purification','purification method'],7:['elution buffer'],8:['buffer exchange'],9:['normalization','normatlization'],10:['post purification sterile filtration','sterile filtration'],11:['aliquoting','aliquots'],12:['shipping container','shipping format'],13:['custom plate map'],14:['restriction enzyme sites to avoid for dna optimization','restriction enzyme sites to avoid for codon optimization'],15:['please indicate if you prefer not to receive physical samples and only data','please indicate if you prefer not to receive any physical samples and only data'],16:['ship with testing pending','ship physical samples with additional service requests pending'],17:['additional requests']}

ALIASES[9].append('Normalization (select Scale for options) Please note: we do not normalize or invoice for samples below target concentration')
ALIASES[11].append('Aliquoting (Not applicable when characterization services and testing are added, select Scale for options)')
ALIASES[12].append('Shipping Container* (select Scale for options)')

def occupied(v):
    return v is not None and str(v).strip() != ''

def norm(v):
    return re.sub(r'[^a-z0-9]+', '', str(v).lower().replace('λ','lambda').replace('κ','kappa'))

def options():
    w = load_workbook(TEMPLATE, read_only=True, data_only=True)
    out = {}; category = None
    for a,b in w['Sheet3'].iter_rows(max_col=2, values_only=True):
        if a: category = a
        if category and b: out.setdefault(category, []).append(b)
    w.close(); out['Cell Line']=['HEK293','CHO']
    return out

def closest(value, choices):
    """Return actual template spelling; expose nonexact choices for review."""
    clean = re.sub(r'^Empty Vector\s*-\s*','',str(value),flags=re.I)
    choices = [c for c in choices if not c.startswith('PLEASE SELECT')]
    for c in choices:
        if norm(clean) == norm(c): return c, 'matched'
    ranked = sorted(((difflib.SequenceMatcher(None,norm(clean),norm(c)).ratio(),c) for c in choices),reverse=True)
    if ranked and ranked[0][0] >= .55:
        return ranked[0][1], 'closest option; review'
    return None, 'no reliable option; original preserved in report'

def set_cell(root, address, value):
    data=root.find(Q('sheetData')); rn=re.search(r'\d+',address).group()
    row=data.find(f"{Q('row')}[@r='{rn}']")
    if row is None:
        row=ET.Element(Q('row'),r=rn)
        following=next((r for r in data if int(r.get('r'))>int(rn)),None)
        if following is None: data.append(row)
        else: data.insert(data.index(following),row)
    cell=row.find(f"{Q('c')}[@r='{address}']")
    if cell is None:
        cell=ET.SubElement(row,Q('c'),r=address)
        # Copy template input styling from row 4 for added sequence rows.
        model=data.find(f"{Q('row')}[@r='4']/{Q('c')}[@r='{re.sub(r'[0-9]', '',address)}4']")
        if model is not None and model.get('s'): cell.set('s',model.get('s'))
    for child in list(cell): cell.remove(child)
    cell.attrib.pop('t',None)
    if occupied(value):
        cell.set('t','inlineStr'); text=ET.SubElement(ET.SubElement(cell,Q('is')),Q('t'))
        text.set('{http://www.w3.org/XML/1998/namespace}space','preserve'); text.text=str(value)
    # Excel requires cells in column order.
    def col(c):
        n=0
        for ch in re.sub(r'\d','',c.get('r')): n=n*26+ord(ch)-64
        return n
    row[:]=sorted(row,key=col)

def convert(blob):
    opts=options(); issues=[]; count=0
    w=load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
    if 'Antibody Designs' not in w.sheetnames:
        w.close(); raise ValueError('Missing Antibody Designs tab; expected a v4.2 workbook')
    z=zipfile.ZipFile(TEMPLATE); roots={n:ET.fromstring(z.read(n)) for n in z.namelist() if n.startswith('xl/worksheets/') and n.endswith('.xml')}
    seq=roots['xl/worksheets/sheet3.xml']; details=roots['xl/worksheets/sheet4.xml']
    def report(location,original,result,status):
        issues.append({'location':location,'original':original,'selected':result,'status':status,'version':VERSION})
    # Clear template placeholders, preserving every style and instructional row.
    for c in list(seq.find(Q('sheetData')).iter(Q('c'))):
        if int(re.search(r'\d+',c.get('r')).group())>=4: set_cell(seq,c.get('r'),None)
    try:
        for source_row,row in enumerate(w['Antibody Designs'].iter_rows(min_row=4,max_col=37,values_only=True),4):
            if not occupied(row[2]): continue
            if any(occupied(v) for v in row[22:]):
                raise ValueError(f'Antibody Designs row {source_row}: bispecific/extra-construct fields cannot be represented in v3.1')
            count+=1; target=count+3
            if target>1048576: raise ValueError('Too many designs for Excel')
            vals={dest:row[ord(src)-65] for src,dest in MAP.items()}
            # Use source isotype when representable; retain sample-confirmed mini-binder mapping.
            two=occupied(vals.get('S')) or occupied(vals.get('M'))
            original_isotype=vals.get('D')
            if norm(original_isotype) == 'minibinder':
                vals['D']='hIgG1' if two else 'hIgG1 VHH Fc Fusion'
                report(f'Antibody Designs!G{source_row}',original_isotype,vals['D'],'mini-binder mapping matching supplied example; review')
            elif not occupied(original_isotype):
                vals['D']='hIgG1' if two else 'hIgG1 VHH Fc Fusion'
                report(f'Antibody Designs!G{source_row}',None,vals['D'],'chain-based inference; review')
            if not two: vals['E']='N/A'
            for col,cat in GROUPS.items():
                v=vals.get(col)
                if not occupied(v): continue
                # Custom nucleotide sequences must never be fuzzy-replaced.
                if col in ('I','K','P','R') and re.fullmatch(r'[ACGTUNacgtun\s]+',str(v)): continue
                selected,status=closest(v,opts[cat])
                if selected is None and col in ('G','N'): selected=v; status='custom vector retained; review'
                vals[col]=selected
                if status!='matched': report(f'Antibody Designs!{get_column_letter(ord(col)-64+3) if col!="C" else "C"}{source_row}',v,selected,status)
            for col in 'ABCDEFGHIJKLMNOPQRS': set_cell(seq,f'{col}{target}',vals.get(col))
        # Source field names, never row positions, drive Order Details mapping.
        for r in range(3,18):
            set_cell(details,f'B{r}',None); set_cell(details,f'C{r}',None)
        labels={}
        tw=load_workbook(TEMPLATE,read_only=True,data_only=True)
        for r in range(3,18): labels[r]=[norm(tw['Order Details'].cell(r,1).value)]+[norm(a) for a in ALIASES[r]]
        tw.close(); seen=set()
        source=next((w[n] for n in ('Antibody Settings','Order Details') if n in w.sheetnames),None)
        if source is None: report('Order Details',None,None,'source settings tab absent; all inputs left blank')
        else:
            for cells in source.iter_rows(values_only=True):
                if not cells or not occupied(cells[0]): continue
                label=norm(cells[0])
                if label in ('antibodycustomizations','orderdetailsrequired','orderdetails'): continue
                matches=[r for r,aliases in labels.items() if label in aliases]
                if not matches:
                    ranked=sorted((max(difflib.SequenceMatcher(None,label,a).ratio() for a in aa),r) for r,aa in labels.items())
                    if ranked[-1][0]>=.8 and ranked[-1][0]-ranked[-2][0]>=.08: matches=[ranked[-1][1]]
                value=cells[1] if len(cells)>1 else None; note=cells[2] if len(cells)>2 else None
                if not occupied(value) and not occupied(note): continue
                if not matches:
                    report(f'{source.title}:{cells[0]}',value,None,'unmapped field; review'); continue
                r=matches[0]
                if r in seen: report(f'Order Details:{cells[0]}',value,None,'duplicate field ignored; review'); continue
                seen.add(r)
                if occupied(value):
                    if r in ORDER_CATEGORIES:
                        selected,status=closest(value,opts[ORDER_CATEGORIES[r]])
                        if status!='matched': report(f'Order Details!B{r}',value,selected,status)
                        set_cell(details,f'B{r}',selected)
                        if selected is None: note=f'{note or ""} [Original selection: {value}]'.strip()
                    else: set_cell(details,f'B{r}',value)
                if occupied(note): set_cell(details,f'C{r}',note)
        if 'Contact Information' in w.sheetnames:
            contact=roots['xl/worksheets/sheet2.xml']
            template_contact=load_workbook(TEMPLATE,read_only=True,data_only=True)
            positions={}
            for rr in range(4,30):
                key=norm(template_contact['Contact Information'].cell(rr,1).value)
                if occupied(template_contact['Contact Information'].cell(rr,1).value): positions.setdefault(key,[]).append(rr)
            occurrence={}
            for row in w['Contact Information'].iter_rows(max_col=2,values_only=True):
                if not occupied(row[0]): continue
                label=norm(row[0]); index=occurrence.get(label,0)
                if label in positions:
                    occurrence[label]=index+1
                    if index<len(positions[label]) and occupied(row[1]): set_cell(contact,f'B{positions[label][index]}',row[1])
            template_contact.close()
        # Refresh cached results for the template's SEARCH-based completion formulas.
        lookup=load_workbook(TEMPLATE,read_only=True,data_only=True)
        search_values=[str(r[0]).lower() for r in lookup['Sheet3'].iter_rows(min_row=21,max_row=75,min_col=2,max_col=2,values_only=True) if occupied(r[0])]
        lookup.close()
        for c in details.iter(Q('c')):
            f=c.find(Q('f'))
            if f is not None and f.text and 'SEARCH(Sheet3!$B$21:$B$75,B' in f.text:
                address='B'+re.search(r'\d+',c.get('r')).group()
                target=details.find(f".//{Q('c')}[@r='{address}']")
                value=''.join(target.itertext()).lower() if target is not None else ''
                cached=c.find(Q('v'))
                if cached is None: cached=ET.SubElement(c,Q('v'))
                cached.text='1' if any(v in value for v in search_values) else '0'
        dimension=seq.find(Q('dimension'))
        dimension.set('ref',f'A1:S{max(4568,count+3)}')
        # Remove standard and extended dropdown controls, retain other validation.
        for root in roots.values():
            for el in list(root.iter()):
                if ET.QName(el).localname=='dataValidation' and el.get('type')=='list': el.getparent().remove(el)
            for el in list(root.iter()):
                if ET.QName(el).localname=='dataValidations':
                    if len(el)==0: el.getparent().remove(el)
                    else: el.set('count',str(len(el)))
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dest:
            for entry in z.infolist(): dest.writestr(entry,ET.tostring(roots[entry.filename],xml_declaration=True,encoding='UTF-8',standalone=True) if entry.filename in roots else z.read(entry.filename))
        return out.getvalue(),count,issues
    finally: w.close(); z.close()

def run_batch(uploaded, output_dir='converted'):
    outdir=Path(output_dir); outdir.mkdir(parents=True,exist_ok=True); results=[]
    for name,blob in uploaded.items():
        if not name.lower().endswith('.xlsx'): continue
        stem=Path(name.replace('\\','/')).stem
        content,count,issues=convert(blob)
        base=f'{stem}_converted_v{VERSION}'
        path=outdir/f'{base}.xlsx'; path.write_bytes(content)
        report={'input':name,'converter_version':VERSION,'design_count':count,'review_items':issues}
        report_path=outdir/f'{base}_report.json'; report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str))
        archive=outdir/f'{base}.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(path,path.name); z.write(report_path,report_path.name)
        results.append(archive)
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('inputs',nargs='+',type=Path); p.add_argument('--output-dir',default='converted'); a=p.parse_args()
    for path in run_batch({p.name:p.read_bytes() for p in a.inputs},a.output_dir): print(path)
