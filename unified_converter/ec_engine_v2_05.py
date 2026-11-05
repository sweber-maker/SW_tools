import io,re,zipfile,os,collections,copy,json,csv
import openpyxl
from openpyxl.utils import get_column_letter

def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def populated(v): return v is not None and str(v).strip() and not str(v).lstrip().startswith('=') and 'PLEASE SELECT OPTION' not in str(v).upper()
def seq(v): return str(v).strip() if populated(v) else None

def find_input(wb):
    # Contents take precedence over worksheet names (v4.2 uses Antibody Designs).
    for ws in wb:
        if norm(ws.title)=='antibodydesigns' and norm(ws.cell(3,15).value).startswith('construct1sequence'):
            return ws,'v42'
    for ws in wb:
        if 'sequence' in ws.title.lower():
            heads=[norm(ws.cell(1,i).value) for i in range(1,min(ws.max_column,45)+1)]
            if any('vhvdjsequence' in h for h in heads) or any('construct1sequence' in h for h in heads):return ws,'legacy'
    if 'Data entry' in wb.sheetnames and norm(wb['Data entry'].cell(3,6).value)=='vhvdjsequencednaoraa':
        return wb['Data entry'],'ec'
    raise ValueError('Cannot find supported worksheet (v4.2, EC Data entry or legacy Sequence).')

def parse(wb):
    ws,kind=find_input(wb)
    rows=[]
    if kind=='v42':
        for r in range(4,ws.max_row+1):
            name=ws.cell(r,3).value; first=seq(ws.cell(r,15).value); second=seq(ws.cell(r,22).value)
            if not populated(name) or not first:continue
            if seq(ws.cell(r,30).value) or seq(ws.cell(r,37).value):raise ValueError(f'Row {r}: 3 or 4 constructs unsupported')
            rows.append(dict(row=r,name=str(name).strip(),pur=ws.cell(r,4).value,tag=ws.cell(r,6).value,iso=ws.cell(r,7).value,well=ws.cell(r,2).value,plate=ws.cell(r,1).value,chains=[{'name':ws.cell(r,9).value,'sequence':first,'vector':ws.cell(r,10).value,'kozak':ws.cell(r,12).value,'leader':ws.cell(r,14).value}]+([{'name':ws.cell(r,16).value,'sequence':second,'vector':ws.cell(r,17).value,'kozak':ws.cell(r,19).value,'leader':ws.cell(r,21).value}] if second else [])))
    elif kind=='ec':
        h={norm(ws.cell(3,c).value):c for c in range(1,ws.max_column+1)}
        def get(r,key):return ws.cell(r,h[key]).value if key in h else None
        for r in range(4,ws.max_row+1):
            name=get(r,'iggname'); first=seq(get(r,'vhvdjsequencednaoraa'));second=seq(get(r,'vlsequencednaoraa'))
            if not populated(name) or not first:continue
            fmt=get(r,'format')
            rows.append(dict(row=r,name=str(name).strip(),pur=None,tag=None,iso=fmt,well=get(r,'well'),plate=get(r,'plate'),chains=[{'name':get(r,'vhname'),'sequence':first,'vector':get(r,'vhvectornameinsertionsitename'),'kozak':get(r,'vhkozaksequencedna'),'leader':get(r,'vhleadersequencedna')}]+([{'name':get(r,'vlname'),'sequence':second,'vector':get(r,'vlvectornameinsertionsitename'),'kozak':get(r,'vlkozaksequencedna'),'leader':get(r,'vlleadersequencedna')}] if second else [])))
    else:
        h={norm(ws.cell(1,c).value):c for c in range(1,ws.max_column+1)}
        def get(r,key):return ws.cell(r,h[key]).value if key in h else None
        for r in range(2,ws.max_row+1):
            name=get(r,'iggname') or get(r,'antibodyname'); first=seq(get(r,'vhvdjsequencednaoraa') or get(r,'construct1sequencednaoraa'));second=seq(get(r,'vlsequencednaoraa') or get(r,'construct2sequencednaoraa'))
            if not populated(name) or not first:continue
            rows.append(dict(row=r,name=str(name).strip(),pur=get(r,'purification'),tag=get(r,'histagsequence'),iso=get(r,'iggisotype'),well=get(r,'well'),plate=get(r,'plate'),chains=[{'name':get(r,'vhname'),'sequence':first,'vector':get(r,'vhvectornameinsertionsitename'),'kozak':get(r,'vhkozaksequencedna'),'leader':get(r,'vhleadersequencedna')}]+([{'name':get(r,'vlname'),'sequence':second,'vector':get(r,'vlvectornameinsertionsitename'),'kozak':get(r,'vlkozaksequencedna'),'leader':get(r,'vlleadersequencedna')} ] if second else [])))
    if not rows:raise ValueError('No antibody rows with a sequence found.')
    return rows,ws.title


def parse_csv_rows(source_bytes):
    """CSV export: each construct is a separate row; pair by IgG Name and validate roles."""
    sample=source_bytes.decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(sample))
    required={'IgG Name','Construct Name (DNA)','Insert Sequence (DNA)'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError('CSV not recognized: missing '+', '.join(sorted(required-set(reader.fieldnames or []))))
    groups=collections.OrderedDict()
    for line,rec in enumerate(reader,start=2):
        name=(rec.get('IgG Name') or '').strip(); sequence=seq(rec.get('Insert Sequence (DNA)'))
        if not name or not sequence: continue
        cname=(rec.get('Construct Name (DNA)') or '').strip()
        lower=cname.lower()
        vh=bool(re.search(r'(?<![a-z])(?:vh|heavy)(?![a-z])',lower))
        vl=bool(re.search(r'(?<![a-z])(?:vl|light)(?![a-z])',lower))
        if vh==vl:raise ValueError(f'CSV line {line}: cannot identify uniquely heavy versus light chain from {cname!r}')
        chain={'name':cname,'sequence':sequence,'vector':rec.get('Vector Name'),'kozak':rec.get('Kozak Sequence (DNA)'),'leader':rec.get('Leader Sequence (DNA)')}
        key=(rec.get('Plate (fixed plate maps)') or '').strip(),(rec.get('Well (fixed plate maps)') or '').strip(),name
        entry=groups.setdefault(name, {'row':line,'name':name,'pur':None,'tag':None,'iso':'hIgG1' if 'IgG' in (rec.get('Product Type') or '') else None,'well':key[1], 'plate':key[0], '_chain_map':{}})
        if entry['well']!=key[1] or entry['plate']!=key[0]:raise ValueError(f'{name}: inconsistent source plate/well coordinates')
        role='VH' if vh else 'VL'
        if role in entry['_chain_map']:raise ValueError(f'{name}: multiple {role} rows')
        entry['_chain_map'][role]=chain
    rows=[]
    for name,entry in groups.items():
        if set(entry['_chain_map'])!={'VH','VL'}:raise ValueError(f'{name}: require exactly one VH and one VL row')
        entry['chains']=[entry['_chain_map']['VH'],entry['_chain_map']['VL']]
        del entry['_chain_map'];rows.append(entry)
    if not rows:raise ValueError('No paired IgG rows in CSV')
    return rows,'CSV / paired VH and VL construct rows'

def mode(rows,filename,wb):
    lengths=set(map(lambda r:len(r['chains']),rows))
    if len(lengths)>1:raise ValueError('Mixed one- and two-chain rows: split inputs before conversion.')
    chains=lengths.pop(); pur=[str(r['pur'] or '').lower() for r in rows if populated(r['pur'])]
    found=set('nickel' if ('his' in p or 'nickel' in p or 'ni-' in p) else 'none' if ('supe' in p or 'supernatant' in p or 'none' in p or 'no purification' in p) else 'protein-a' if ('protein a' in p or 'proa' in p) else 'unknown' for p in pur)-{'unknown'}
    if len(found)>1:raise ValueError('Mixed purification methods; split before conversion.')
    hints=filename.lower()
    if not found:
        if re.search(r'(^|\W)(his|nickel|ni)(\W|$)',hints):found={'nickel'}
        elif 'supe' in hints or 'none' in hints:found={'none'}
        elif 'proa' in hints or 'protein' in hints:found={'protein-a'}
    # Never infer a purification from a generic sample template. Explicit fallback is reported.
    purification=next(iter(found)) if found else ('protein-a' if chains==2 else 'none')
    settings=' '.join(str(c.value or '') for s in wb if 'settings' in s.title.lower() for row in s.iter_rows(min_row=1,max_row=min(s.max_row,18),max_col=min(s.max_column,3)) for c in row).lower() if wb is not None else ''
    container='tube' if (re.search(r'\btubes?\b',hints) or ('shipping container' in settings and re.search(r'\btubes?\b',settings) and '96-well' not in settings)) else 'plate'
    return chains,purification,container,not bool(found)

def dropdown_choices(workbook, worksheet, coordinate):
    """Read exact strings from the XLSX's own list validation (named ranges or literals)."""
    from openpyxl.utils.cell import range_boundaries
    cell=worksheet[coordinate]
    for dv in worksheet.data_validations.dataValidation:
        if dv.type!='list' or not any(cell.coordinate in worksheet[rng] if False else _covers(rng,cell.row,cell.column) for rng in dv.sqref.ranges):
            continue
        formula=(dv.formula1 or '').strip()
        if formula.startswith('='):formula=formula[1:]
        if formula.startswith('"') and formula.endswith('"'):
            return formula[1:-1].split(',')
        defined=workbook.defined_names.get(formula)
        if defined is not None:
            vals=[]
            for name,rect in defined.destinations:
                target=workbook[name.strip("'")]
                area=target[rect]
                if not isinstance(area,tuple):area=((area,),)
                elif area and not isinstance(area[0],tuple):area=(area,)
                vals.extend(x.value for row in area for x in row if x.value is not None)
            return vals
        if '!' in formula:
            name,rect=formula.rsplit('!',1)
            area=workbook[name.strip("'")][rect]
            if not isinstance(area,tuple):area=((area,),)
            elif area and not isinstance(area[0],tuple):area=(area,)
            return [x.value for row in area for x in row if x.value is not None]
    return None

def _covers(rng,row,col):
    return rng.min_row<=row<=rng.max_row and rng.min_col<=col<=rng.max_col

def match_dropdown(value,choices):
    """Return an exact dropdown choice if confident; otherwise return the input verbatim."""
    import difflib
    if not choices:return value,'no validation'
    if value in choices:return value,'exact'
    if value is None or not str(value).strip():return value,'empty'
    actual=[c for c in choices if norm(c)==norm(value)]
    if len(actual)==1:return actual[0],'normalized'
    # Ignore generic placeholders; require a very close unique match.
    candidates=[(difflib.SequenceMatcher(None,str(value).casefold(),str(c).casefold()).ratio(),c)
                for c in choices if 'custom - enter vector name' not in str(c).casefold()]
    candidates.sort(key=lambda x:x[0],reverse=True)
    if candidates and candidates[0][0]>=0.92 and (len(candidates)==1 or candidates[0][0]-candidates[1][0]>=0.07):
        return candidates[0][1],'fuzzy'
    return value,'verbatim'

def extend_validations(worksheet,last_row):
    """Templates validate rows 4:18; extend the existing rules to cover all populated output rows."""
    from openpyxl.worksheet.cell_range import CellRange,MultiCellRange
    for dv in worksheet.data_validations.dataValidation:
        expanded=[]
        for region in dv.sqref.ranges:
            cr=CellRange(str(region))
            if cr.min_row==4 and cr.max_row<last_row:
                cr.max_row=last_row
            expanded.append(str(cr))
        dv.sqref=MultiCellRange(' '.join(expanded))

def convert_to_v42(rows, source_name, template_bytes):
    """Map normalized EC or paired-row CSV into original v4.2 workbook structure."""
    import difflib
    dest=openpyxl.load_workbook(io.BytesIO(template_bytes))
    ws=dest['Antibody Designs']
    # Source v4.2 was a filled-in sample: clear customer-specific contact and assay selections.
    if 'Contact Information' in dest:
        contact=dest['Contact Information']
        for rr in range(4,contact.max_row+1):
            field=str(contact.cell(rr,1).value or '').lower()
            if any(k in field for k in ('name','company','department','address','city','state','zip','country','phone','email','shipping','billing','purchase order','customer','contact')):
                contact.cell(rr,2).value=None
    if 'Antibody Settings' in dest:
        settings=dest['Antibody Settings']
        for rr in range(3,settings.max_row+1):
            if settings.cell(rr,1).value and settings.cell(rr,2).data_type!='f':settings.cell(rr,2).value=None
    if 'Characterization Add-ons' in dest:
        addon=dest['Characterization Add-ons']
        for row in addon.iter_rows(min_row=3):
            for cell in row[2:]:
                if cell.data_type!='f' and cell.value is not None and (str(cell.value).strip().lower()=='yes' or (cell.column==3 and str(cell.value).strip().lower() in ('no','n/a'))):cell.value=None
    warnings=[]
    def choice(r,col,v):
        if v is None:return None
        opts=dropdown_choices(dest,ws,f'{get_column_letter(col)}4')
        result,status=match_dropdown(v,opts)
        if status=='verbatim' and opts:
            warnings.append(f'{r}: column {get_column_letter(col)}: original {v!r} preserved (not in dropdown)')
        return result
    # Clear only actual antibody data. Preserve formula scaffolding and workbook dropdowns.
    for r in range(4,ws.max_row+1):
        for c in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37]:
            cell=ws.cell(r,c)
            if cell.data_type!='f':cell.value=None
    for index,record in enumerate(rows):
        r=index+4
        if r>ws.max_row:raise ValueError('v4.2 maximum number of rows exceeded')
        cs=record['chains']
        pur=record['pur']
        if not populated(pur):
            hints=source_name.lower()
            pur=('Nickel' if 'nickel' in hints or re.search(r'\bhis\b',hints) else 'None' if 'none' in hints or 'supe' in hints else 'Protein A' if ('proa' in hints or 'protein-a' in hints) else None)
            if not pur:warnings.append(f'{record["name"]}: purification not represented in EC/sequence input; left blank')
        fmt=str(record['iso'] or '').strip()
        if fmt=='VHH-Fc-IgG1':fmt='hIgG1 VHH Fc Fusion'
        elif fmt in ('hIgG1','hIgG2','hIgG4'):pass
        elif fmt=='Fab':fmt='Fab'
        else:
            if fmt:warnings.append(f'{record["name"]}: isotype {fmt!r} copied or best matched; review')
        fields={1:record['plate'],2:record['well'],3:record['name'],4:pur,7:fmt,
                9:cs[0]['name'],10:cs[0]['vector'],12:cs[0]['kozak'],14:cs[0]['leader'],15:cs[0]['sequence']}
        if len(cs)==2:fields.update({16:cs[1]['name'],17:cs[1]['vector'],19:cs[1]['kozak'],21:cs[1]['leader'],22:cs[1]['sequence']})
        for col,value in fields.items():
            if value is not None:ws.cell(r,col).value=choice(record['name'],col,value)
        # Set Kozak / leader manual control in v4.2 to avoid conflicting implied built-ins.
        for col,sequence_col,setting in ((11,12,'Custom'),(13,14,'Custom'),(18,19,'Custom'),(20,21,'Custom')):
            if len(cs)==1 and col in (18,20):continue
            if ws.cell(r,sequence_col).value:
                opts=dropdown_choices(dest,ws,f'{get_column_letter(col)}4') or []
                match=next((v for v in opts if 'custom' in str(v).lower()),None)
                if match:ws.cell(r,col).value=match
                else:warnings.append(f'{record["name"]}: no verified custom selection for {get_column_letter(col)}; setting left blank')
        if r!=4:
            for c in range(1,38):
                if not ws.cell(r,c).has_style:ws.cell(r,c)._style=copy.copy(ws.cell(4,c)._style)
    notes=f'Input: {source_name}\nOutput: v4.2\nAntibodies: {len(rows)}\nWarnings: {len(warnings)}\n'+'\n'.join(warnings)
    out=io.BytesIO();dest.save(out)
    check=openpyxl.load_workbook(io.BytesIO(out.getvalue()),read_only=True)['Antibody Designs']
    assert all(check.cell(i+4,15).value==v['chains'][0]['sequence'] for i,v in enumerate(rows))
    assert all(check.cell(i+4,22).value==v['chains'][1]['sequence'] for i,v in enumerate(rows) if len(v['chains'])==2)
    return out.getvalue(),notes,dict(rows=len(rows),warnings=warnings,direction='to_v42')

def convert_routed(source_bytes,source_name,zip_bytes,v42_template_bytes):
    """Returns list of (output suffix, XLSX bytes, report text, metadata)."""
    if source_name.lower().endswith('.csv'):
        rows,_=parse_csv_rows(source_bytes)
        outputs=[]
        ec_data,ec_report,ec_meta=convert_bytes(source_bytes,source_name,zip_bytes)
        outputs.append(('_EC',ec_data,ec_report,ec_meta))
        v42_data,v42_report,v42_meta=convert_to_v42(rows,source_name,v42_template_bytes)
        outputs.append(('_v4.2',v42_data,v42_report,v42_meta))
        return outputs
    wb=openpyxl.load_workbook(io.BytesIO(source_bytes))
    ws,kind=find_input(wb)
    if kind=='ec':
        rows,_=parse(wb)
        data,report,meta=convert_to_v42(rows,source_name,v42_template_bytes)
        return [('_v4.2',data,report,meta)]
    if kind=='v42':
        data,report,meta=convert_bytes(source_bytes,source_name,zip_bytes)
        return [('_EC',data,report,meta)]
    # Older legacy Sequence forms are routed to EC for backward compatibility.
    data,report,meta=convert_bytes(source_bytes,source_name,zip_bytes)
    return [('_EC',data,report,meta)]

def convert_bytes(source_bytes, source_name, zip_bytes):
    if source_name.lower().endswith('.csv'):
        source=None; rows,sheet=parse_csv_rows(source_bytes)
    else:
        source=openpyxl.load_workbook(io.BytesIO(source_bytes));rows,sheet=parse(source)
    chains,pur,container,defaulted=mode(rows,source_name,source)
    archive=zipfile.ZipFile(io.BytesIO(zip_bytes)); group='igg' if chains==2 else 'vhh'
    matches=[n for n in archive.namelist() if f'-{group}-{pur}-' in n.lower() and ('_plate' in n.lower() if container=='plate' else ('_tube' in n.lower()))]
    if len(matches)!=1:raise ValueError(f'Expected 1 template for {group}/{pur}/{container}, found {matches}')
    dest=openpyxl.load_workbook(io.BytesIO(archive.read(matches[0])));ws=dest['Data entry'];hdr={norm(ws.cell(3,c).value):c for c in range(1,ws.max_column+1)}
    warnings=[];counts=collections.Counter()
    # Inspect original validation definitions before extending; names resolve to exact hidden list values.
    validation_columns={}
    for col in range(1,ws.max_column+1):
        opts=dropdown_choices(dest,ws,f'{get_column_letter(col)}4')
        if opts is not None:validation_columns[col]=opts
    def put(r,alias,value,record_name=None):
        if value is None:return
        for a in alias:
            if norm(a) in hdr:
                col=hdr[norm(a)]
                signal_key=norm(ws.cell(3,col).value)
                if signal_key in ('vhleadersequencedna','vlleadersequencedna','vhkozaksequencedna','vlkozaksequencedna'):
                    chain=rows[r-4]['chains'][0 if signal_key.startswith('vh') else 1]
                    resolved,reason=signal_resolve(value,None,chain['kozak'],chain['sequence'],validation_columns.get(col,[]))
                    if reason:warnings.append(f'{record_name or "Row "+str(r)}: {ws.cell(3,col).value}: {reason}')
                    if not signal_dna(resolved):
                        warnings.append(f'{record_name or "Row "+str(r)}: {ws.cell(3,col).value}: non-DNA value left blank; actual DNA required for manual review')
                        return
                    # DNA fields are literal sequences, never fuzzy-corrected to dropdown strings.
                    value=signal_dna(resolved)
                elif col in validation_columns:
                    exact,status=match_dropdown(value,validation_columns[col])
                    if status=='verbatim':
                        warnings.append(f'{record_name or "Row "+str(r)}: {ws.cell(3,col).value}: {value!r} not confidently matched to dropdown; retained original input verbatim (outside validation list)')
                        if 'vector' in str(ws.cell(3,col).value).lower():counts['verbatim_vectors']+=1
                    if status in ('normalized','fuzzy'):counts['dropdown_corrected']+=1
                    value=exact
                ws.cell(r,col).value=value
                return
    # Clear all bundled example rows and extend them, retaining template structure.
    example=4
    for r in range(4,max(ws.max_row+1,len(rows)+4)):
        for c in range(1,ws.max_column+1):
            cell=ws.cell(r,c)
            if r>example and r<len(rows)+4:
                model=ws.cell(example,c)
                if not cell.has_style:cell._style=copy.copy(model._style)
            cell.value=None
    for idx,record in enumerate(rows):
        r=idx+4;cs=record['chains'];ch=cs[0]
        well=record['well'] if populated(record['well']) else f'{chr(65+(idx%96)%8)}{1+(idx%96)//8}'
        plate=record['plate'] if populated(record['plate']) else 1+idx//96
        if isinstance(well,str) and not re.match(r'^[A-H](?:[1-9]|1[0-2])$',well.strip(),re.I):warnings.append(f'{record["name"]}: unrecognized well {well!r}')
        put(r,['Plate #'],plate);put(r,['Well'],well);put(r,['Plate label'],f'Plate {plate}')
        put(r,['IGG Name'],record['name']);put(r,['VH Name'],ch['name'] or record['name']+'_VH');put(r,['VH (VDJ) Sequence (DNA or AA)'],ch['sequence'])
        fmt=str(record['iso'] or '').strip()
        if chains==1:
            if 'vhh' in fmt.lower() and 'fc' in fmt.lower():fmt='VHH-Fc-IgG1'
            elif 'scfv' in fmt.lower():fmt='scFv-His' if pur=='nickel' else 'scFv'
            elif 'vhh' in fmt.lower():fmt='VHH-His' if pur=='nickel' else 'VHH-Fc-IgG1' if pur=='protein-a' else 'VHH'
            elif not fmt:fmt='VHH-His' if pur=='nickel' else 'VHH-Fc-IgG1' if pur=='protein-a' else 'Other'
        else:
            if 'fab' in source_name.lower():fmt='Fab'
            elif 'fab' in fmt.lower():fmt='Fab'
            elif norm(fmt) in ('higg1','higg2','higg4'):pass
            elif not fmt:fmt='Other';warnings.append(f'{record["name"]}: no exact IgG format; set Other')
            elif fmt not in ('hIgG1','hIgG2','hIgG4','Fab','Other'):fmt='Other';warnings.append(f'{record["name"]}: unrecognized isotype; set Other')
        put(r,['Format'],fmt,record['name'])
        put(r,['His-tag length'],len(re.findall('CAC',str(record['tag'] or '').upper())) if record['tag'] and re.fullmatch(r'(CAC|CAT)+',str(record['tag']).upper()) else 6 if pur=='nickel' else None)
        for aliases,val in [(['VH Vector Name - Insertion Site Name'],ch['vector']),(['VH Kozak Sequence (DNA)'],ch['kozak']),(['VH Leader Sequence (DNA)'],ch['leader'])]:put(r,aliases,val,record['name'])
        if chains==2:
            vl=cs[1];put(r,['VL Name'],vl['name'] or record['name']+'_VL');put(r,['VL Sequence (DNA or AA)'],vl['sequence'])
            for a,v in [(['VL Vector Name - Insertion Site Name'],vl['vector']),(['VL Kozak Sequence (DNA)'],vl['kozak']),(['VL Leader Sequence (DNA)'],vl['leader'])]:put(r,a,v,record['name'])
        counts['rows']+=1;counts['chains']+=chains
    if source_name.lower().endswith('.csv'):
        audit=dest.create_sheet('Original construct vectors')
        audit.append(['IgG Name','Chain','Construct Name','Original Vector Name','Destination dropdown selection','Input CSV line','Notes'])
        for record in rows:
            for i,ch in enumerate(record['chains']):
                a='VH Vector Name - Insertion Site Name' if i==0 else 'VL Vector Name - Insertion Site Name'
                final=ws.cell(rows.index(record)+4,hdr[norm(a)]).value
                audit.append([record['name'],'VH' if i==0 else 'VL',ch['name'],ch['vector'],final,record['row'],'Original preserved verbatim; not a valid dropdown choice' if final not in (dropdown_choices(dest,ws,f'{get_column_letter(hdr[norm(a)])}4') or []) else ''])
        audit.freeze_panes='A2';audit.auto_filter.ref=f'A1:G{audit.max_row}'
        for col,width in {'A':16,'B':10,'C':39,'D':46,'E':50,'F':15,'G':70}.items(): audit.column_dimensions[col].width=width
        warnings.insert(0,'CSV has no purification field: selected Protein A by 2-chain fallback; confirm before ordering' if defaulted else 'Confirm purification selected from input')
    extend_validations(ws,len(rows)+3)
    notes=f'Input: {source_name}\nWorksheet: {sheet}\nTemplate: {matches[0]}\nRows: {len(rows)}; constructs per row: {chains}\nPurification: {pur}'+(' (FALLBACK; review)' if defaulted else '')+f'\nContainer: {container}\nDropdown values auto-corrected: {counts["dropdown_corrected"]}; verbatim vectors: {counts["verbatim_vectors"]}\nWarnings: {len(warnings)}\n'+'\n'.join(warnings)
    out=io.BytesIO();dest.save(out)
    check=openpyxl.load_workbook(io.BytesIO(out.getvalue()),read_only=True)['Data entry']; assert sum(bool(check.cell(r,hdr['vhvdjsequencednaoraa']).value) for r in range(4,len(rows)+4))==len(rows)
    return out.getvalue(),notes,dict(rows=len(rows),constructs=chains,purification=pur,container=container,template=matches[0],warnings=warnings,dropdown_corrected=counts['dropdown_corrected'],verbatim_vectors=counts['verbatim_vectors'])

