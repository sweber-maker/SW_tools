
# Routing + validation: delegates to the unmodified v1.4 / fast-v3.1 conversion engines.
import io,os,csv,json,traceback,zipfile
from pathlib import Path
VERSION = "2.03"

def kind_from_source(blob,name):
    if name.lower().endswith('.csv'):
        parse_csv_rows(blob)
        return 'sequence_download'
    if not name.lower().endswith('.xlsx'):
        raise ValueError('Only .xlsx and paired-row .csv are supported')
    wb=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
    try:
        if 'Sequence' in wb.sheetnames and wb['Sequence'].cell(2,3).value=='IgG Name':return 'v31'
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
    if kind=='v31':
        v3,count,issues=make_v3_from_v42(blob)
        output.append(('v3.1',v3,count,issues,'Existing v3.1 input normalized onto supplied template'))
    elif kind=='v42':
        rows=sequence_rows(blob,name)
        lengths=sorted(set(len(record['chains']) for record in rows))
        for chains in lengths:
            selected=[record for record in rows if len(record['chains'])==chains]
            part=blob
            if len(lengths)>1:
                source=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
                dest=openpyxl.Workbook();sheet=dest.active;sheet.title='Antibody Designs'
                for values in source['Antibody Designs'].iter_rows(max_row=3,max_col=37,values_only=True):sheet.append(values)
                wanted={record['row'] for record in selected}
                for row_number,values in enumerate(source['Antibody Designs'].iter_rows(min_row=4,max_col=37,values_only=True),4):
                    if row_number in wanted:sheet.append(values)
                if 'Antibody Settings' in source.sheetnames:
                    settings=dest.create_sheet('Antibody Settings')
                    for values in source['Antibody Settings'].iter_rows(values_only=True):settings.append(values)
                buffer=io.BytesIO();dest.save(buffer);dest.close();source.close();part=buffer.getvalue()
            ec,ec_notes,ec_meta=convert_bytes(part,name,EC_TEMPLATES)
            label='EC_upload' if len(lengths)==1 else f'EC_upload_{chains}chain'
            output.append((label,ec,len(selected),ec_meta.get('warnings',[]),ec_notes))
        v3,count,issues=make_v3_from_v42(blob)
        output.append(('v3.1',v3,count,issues,''))
    elif kind=='ec':
        rows=sequence_rows(blob,name)
        v42,notes,meta=convert_to_v42(rows,name,V42_TEMPLATE)
        output.append(('v4.2',v42,len(rows),meta.get('warnings',[]),notes))
    else:
        rows=sequence_rows(blob,name)
        ec,ec_notes,ec_meta=convert_bytes(blob,name,EC_TEMPLATES)
        output.append(('EC_upload',ec,len(rows),ec_meta.get('warnings',[]),ec_notes))
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
        stem=Path(name.replace('\\','/')).stem
        base=f'{stem}_converted_v{VERSION}'
        report=[];warnings=[];generated=[]
        def report_row(label,count,status,detail=''):
            report.append([name,label,count,status,detail,VERSION])
        try:
            inspection=inspect_v42(blob) if name.lower().endswith('.xlsx') else {'extra_rows':[]}
            if inspection['extra_rows']:
                reason='3–4 construct fields found on source rows '+', '.join(map(str,inspection['extra_rows']))
                report_row('v3.1',0,'REJECTED',reason)
                report_row('EC_upload',0,'REJECTED',reason)
                content,audit,errors=fallback_table(inspection)
                generated.append((f'{base}_DNA_constructs_audit.json',json.dumps({'converter_version':VERSION,'source':name,'extra_construct_rows':inspection['extra_rows'],'constructs':audit,'errors':errors},indent=2,default=str).encode()))
                if errors:
                    report_row('DNA_constructs',0,'FAILED','; '.join(errors))
                else:
                    generated.append((f'{base}_DNA_constructs.xlsx',content))
                    count=len(audit)
                    needs_review=any(entry['warnings'] for entry in audit)
                    report_row('DNA_constructs',count,'REVIEW' if needs_review else 'OK','DNA-only fallback; normal conversions rejected')
            else:
                kind,outputs=process_one(blob,name)
                for label,content,count,issues,notes in outputs:
                    generated.append((f'{base}_{label}.xlsx',content))
                    report_row(label,count,'OK',f'{len(issues)} review items')
                    warnings.extend([[name,label,issue] for issue in issues])
                    if notes:generated.append((f'{base}_{label}_notes.txt',notes.encode('utf-8')))
        except Exception as exc:
            report_row('conversion',0,'FAILED',str(exc))
        def csvdata(header,rows):
            out=io.StringIO();writer=csv.writer(out);writer.writerow(header);writer.writerows(rows)
            return out.getvalue().encode('utf-8-sig')
        path=output_dir/f'{base}.zip'
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
            for filename,content in generated:archive.writestr(filename,content)
            archive.writestr(f'{base}_report.csv',csvdata(['Input','Output','Rows','Status','Detail','Converter version'],report))
            archive.writestr(f'{base}_warnings.csv',csvdata(['Input','Output','Warning'],warnings))
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:raise ValueError('Output ZIP integrity check failed')
        archives.append(path)
    return archives
