
# Routing + validation: delegates to the unmodified v1.4 / fast-v3.1 conversion engines.
import io,os,csv,json,traceback,zipfile
from pathlib import Path
VERSION = "2.01"

def kind_from_source(blob,name):
    if name.lower().endswith('.csv'):
        parse_csv_rows(blob)
        return 'sequence_download'
    if not name.lower().endswith('.xlsx'):
        raise ValueError('Only .xlsx and paired-row .csv are supported')
    wb=openpyxl.load_workbook(io.BytesIO(blob),read_only=False,data_only=False)
    try:
        _,kind=find_input(wb)
        return {'v42':'v42','ec':'ec','legacy':'sequence_download'}[kind]
    finally: wb.close()

def make_v3_from_v42(v42_bytes):
    out,count,issues=convert_v3(v42_bytes)
    return out, count, [f"v3.1 {issue['location']}: {issue['status']} | original={issue['original']!r}; selected={issue['selected']!r}" for issue in issues]


def validate_workbook(blob, expected_rows, kind):
    wb=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
    try:
        if kind=='v3.1':
            ws=wb['Sequence']; assert ws.cell(2,3).value=='IgG Name'
            cnt=sum(1 for row in ws.iter_rows(min_row=4,min_col=3,max_col=3,values_only=True) if row[0])
        elif kind=='v4.2':
            ws=wb['Antibody Designs']
            cnt=sum(1 for row in ws.iter_rows(min_row=4,min_col=3,max_col=3,values_only=True) if row[0])
        else:
            ws=wb['Data entry']
            hdr={norm(c.value):c.column for c in ws[3] if c.value}
            assert 'iggname' in hdr
            cnt=sum(1 for row in ws.iter_rows(min_row=4,min_col=hdr['iggname'],max_col=hdr['iggname'],values_only=True) if row[0])
        if cnt!=expected_rows:raise AssertionError(f'Expected {expected_rows} entries, found {cnt} in {kind}')
        return cnt
    finally:wb.close()

def sequence_rows(blob,name):
    if name.lower().endswith('.csv'):
        return parse_csv_rows(blob)[0]
    wb=openpyxl.load_workbook(io.BytesIO(blob))
    try:return parse(wb)[0]
    finally:wb.close()

def process_one(blob,name):
    kind=kind_from_source(blob,name)
    output=[]
    if kind=='v42':
        rows=sequence_rows(blob,name)
        ec,ec_notes,ec_meta=convert_bytes(blob,name,EC_TEMPLATES)
        output.append(('EC',ec,len(rows),ec_meta.get('warnings',[]),ec_notes))
        v3,count,issues=make_v3_from_v42(blob)
        output.append(('v3.1',v3,count,issues,''))
    elif kind=='ec':
        rows=sequence_rows(blob,name)
        v42,notes,meta=convert_to_v42(rows,name,V42_TEMPLATE)
        output.append(('v4.2',v42,len(rows),meta.get('warnings',[]),notes))
    else:
        rows=sequence_rows(blob,name)
        ec,ec_notes,ec_meta=convert_bytes(blob,name,EC_TEMPLATES)
        output.append(('EC',ec,len(rows),ec_meta.get('warnings',[]),ec_notes))
        v42,v42_notes,v42_meta=convert_to_v42(rows,name,V42_TEMPLATE)
        output.append(('v4.2',v42,len(rows),v42_meta.get('warnings',[]),v42_notes))
        v3,count,issues=make_v3_from_v42(v42)
        output.append(('v3.1',v3,count,issues,'Sequence Download via v4.2'))
    for label,content,n,warnings,notes in output:
        validate_workbook(content,n,label)
    return kind,output

def run_unified(uploaded, output_dir='converted'):
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    archives=[]
    for name,blob in uploaded.items():
        kind,outputs=process_one(blob,name)
        stem=Path(name.replace('\\','/')).stem
        base=f'{stem}_converted_v{VERSION}'
        report=[];warnings=[];generated=[]
        for label,content,count,issues,notes in outputs:
            filename=f'{base}_{label}.xlsx'
            generated.append((filename,content))
            report.append([name,kind,label,count,len(issues),'OK',VERSION])
            warnings.extend([[name,label,issue] for issue in issues])
            if notes: generated.append((f'{base}_{label}_notes.txt',notes.encode('utf-8')))
        def csvdata(header,rows):
            out=io.StringIO();writer=csv.writer(out);writer.writerow(header);writer.writerows(rows)
            return out.getvalue().encode('utf-8-sig')
        path=output_dir/f'{base}.zip'
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
            for filename,content in generated: archive.writestr(filename,content)
            archive.writestr(f'{base}_report.csv',csvdata(['Input','Detected format','Output','Antibodies','Warnings','Status','Converter version'],report))
            archive.writestr(f'{base}_warnings.csv',csvdata(['Input','Output','Warning'],warnings))
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None: raise ValueError('Output ZIP integrity check failed')
        archives.append(path)
    return archives
