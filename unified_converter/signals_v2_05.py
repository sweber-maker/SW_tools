"""Resolve signal-field instructions only from explicit source settings or exact DNA evidence."""
import io
import re
import zipfile
from lxml import etree as ET
import openpyxl

Q=lambda name:'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'+name

def dna(value):
    result=re.sub(r'\s+','',str(value or '')).upper()
    return result if re.fullmatch('[ACGT]+',result) else None

def instruction(value):
    return bool(re.search(r'please select|replace.{0,80}dropdown|enter.{0,50}sequence|fully contained|partially contained|twist sequence|(?:twist|custom) vector',str(value or ''),re.I))

def norm(value):return re.sub('[^a-z0-9]','',str(value or '').lower())

def resolve(value,setting,kozak,insert,candidates):
    """Never reverse translate or infer a custom leader boundary from an AA insert."""
    if dna(value):return dna(value),None
    if value is not None and str(value).strip() and not instruction(value):return value,None
    known=list(dict.fromkeys(dna(candidate) for candidate in candidates if dna(candidate)))
    if norm(setting)=='twistsequence' and len(known)==1:
        return known[0],'resolved from explicit Twist Sequence setting and source-defined DNA'
    sequence=dna(insert);k=dna(kozak)
    matches=[candidate for candidate in known if sequence and (sequence.startswith(candidate) or (k and sequence.startswith(k+candidate)))]
    if len(matches)==1:return matches[0],'resolved from exact known DNA at insert start'
    if instruction(value):return None,'unresolved instruction cleared; actual DNA is required for manual review'
    return value,None

def definitions(workbook,category):
    candidates=[]
    for title in ('Dropdown Lists','Sheet3'):
        if title not in workbook.sheetnames:continue
        active=False
        for row in workbook[title].iter_rows(max_col=2,values_only=True):
            if row[0] is not None and str(row[0]).strip():active=norm(row[0])==norm(category)
            if active and dna(row[1]):candidates.append(dna(row[1]))
    return list(dict.fromkeys(candidates))

def prepare(blob):
    """Return an in-memory value correction; original customer bytes are never overwritten."""
    if not isinstance(blob,(bytes,bytearray)) or not bytes(blob).startswith(b'PK'):return blob,[]
    workbook=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
    try:
        if 'Antibody Designs' in workbook.sheetnames:
            title='Antibody Designs';fields=((11,10,11,14,'Kozak Sequence','VH Kozak'),(13,12,11,14,'Leader Sequence','VH leader'),(18,17,18,21,'Kozak Sequence','VL Kozak'),(20,19,18,21,'Leader Sequence','VL leader'))
            max_col=37
        elif 'Sequence' in workbook.sheetnames and workbook['Sequence'].cell(2,3).value=='IgG Name':
            title='Sequence';fields=((8,7,8,11,'Kozak Sequence','VH Kozak'),(10,9,8,11,'Leader Sequence','VH leader'),(15,14,15,18,'Kozak Sequence','VL Kozak'),(17,16,15,18,'Leader Sequence','VL leader'))
            max_col=19
        else:return blob,[]
        options={category:definitions(workbook,category) for category in ('Kozak Sequence','Leader Sequence')}
        updates={};audit=[]
        for row_number,row in enumerate(workbook[title].iter_rows(min_row=4,max_col=max_col,values_only=True),4):
            if not row[2]:continue
            for column,setting,kcol,insert,category,label in fields:
                # Do not populate an absent chain's signal fields.
                if not row[insert]:continue
                value=row[column]
                if dna(value):continue
                if value is not None and str(value).strip() and not instruction(value):continue
                selected,reason=resolve(value,row[setting],row[kcol],row[insert],options[category])
                if not reason:continue
                address=f'{openpyxl.utils.get_column_letter(column+1)}{row_number}'
                updates[address]=selected
                audit.append({'location':f'{title}!{address}','field':label,'original':value,'selected':selected,'status':reason})
        if not updates:return blob,[]
        # Resolve sheet path via relationships rather than relying on sheet numbering.
        package=zipfile.ZipFile(io.BytesIO(blob));book=ET.fromstring(package.read('xl/workbook.xml'));rels=ET.fromstring(package.read('xl/_rels/workbook.xml.rels'))
        sheet=next(node for node in book.find(Q('sheets')) if node.get('name')==title)
        rid=sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        target=next(node.get('Target') for node in rels if node.get('Id')==rid)
        path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        root=ET.fromstring(package.read(path))
        for address,selected in updates.items():
            number=re.search(r'\d+',address).group();sheet_data=root.find(Q('sheetData'))
            row=sheet_data.find(f"{Q('row')}[@r='{number}']")
            cell=row.find(f"{Q('c')}[@r='{address}']")
            if cell is None:
                cell=ET.SubElement(row,Q('c'),r=address)
            for child in list(cell):cell.remove(child)
            cell.attrib.pop('t',None)
            if selected is not None:
                cell.set('t','inlineStr');ET.SubElement(ET.SubElement(cell,Q('is')),Q('t')).text=selected
            def column_index(node):
                index=0
                for letter in re.sub(r'\d','',node.get('r')):index=index*26+ord(letter)-64
                return index
            row[:]=sorted(row,key=column_index)
        result=io.BytesIO()
        with zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED) as output:
            for entry in package.infolist():output.writestr(entry,ET.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True) if entry.filename==path else package.read(entry.filename))
        package.close()
        return result.getvalue(),audit
    finally:workbook.close()
