"""Compare a private vendor-final CSV to the independently generated Summit DNA fallback.

This is a reference checker, not a new supported input route or an assembly-rule change.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile
import openpyxl
from engine import load_engine

ROOT=Path(__file__).resolve().parent
CATALOG=ROOT/'summit_final_reference.json'

def dna(value):return re.sub(r'\s+','',str(value or '')).upper()
def vector(value):return re.sub('[^a-z0-9]','',re.sub(r'^Empty Vector\s*-\s*','',str(value or ''),flags=re.I).lower())

def compare(rows, fallback):
    required={'Name','Vector name','Insertion point name','Insert sequence','Construct sequence','Insert length','Construct length','Vector length'}
    if not rows or not required.issubset(rows[0]):raise ValueError('Missing vendor-final reference columns or no rows')
    names=[row['Name'].strip() for row in rows]
    source_names=[row[0] for row in fallback]
    if len(names)!=len(set(names)) or len(source_names)!=len(set(source_names)):raise ValueError('Duplicate construct names require review')
    expected={row[0]:(dna(row[1]),vector(row[2])) for row in fallback}
    checks={'same_name_set':set(names)==set(expected),'insert_dna_matches':0,'vector_site_matches':0,'unambiguous_dna':0,'insert_length_matches':0,'construct_length_matches':0,'insert_occurs_once':0}
    differences=[];replacement=collections.Counter()
    for index,row in enumerate(rows,1):
        name=row['Name'].strip();insert=dna(row['Insert sequence']);construct=dna(row['Construct sequence'])
        reference=expected.get(name)
        conditions={'insert_dna_matches':reference is not None and insert==reference[0],
                    'vector_site_matches':reference is not None and vector(row['Vector name']+'-'+row['Insertion point name'])==reference[1],
                    'unambiguous_dna':bool(re.fullmatch('[ACGT]+',insert)) and bool(re.fullmatch('[ACGT]+',construct)),
                    'insert_length_matches':len(insert)==int(row['Insert length']),
                    'construct_length_matches':len(construct)==int(row['Construct length']),
                    'insert_occurs_once':bool(insert) and construct.count(insert)==1}
        for key,valid in conditions.items():
            checks[key]+=int(valid)
            if not valid:differences.append({'reference_row':index,'check':key})
        replacement[int(row['Insert length'])+int(row['Vector length'])-int(row['Construct length'])]+=1
    passed=checks['same_name_set'] and len(rows)==len(fallback) and not differences
    return {'status':'passed' if passed else 'failed','reference_rows':len(rows),'fallback_constructs':len(fallback),'checks':checks,'differences':differences,'vector_bases_replaced_histogram':dict(replacement),'limits':'DNA identity and supplied metadata checks only; this does not establish biological function or verify an independent vector reference.'}

def check(source,reference,notebook):
    expected=json.loads(CATALOG.read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=expected['source_sha256']:raise ValueError('Summit workbook does not match the registered fixture hash')
    if hashlib.sha256(reference.read_bytes()).hexdigest()!=expected['reference_sha256']:raise ValueError('Final CSV does not match the registered fixture hash')
    n=load_engine(notebook);inspection=n['inspect_v42'](source.read_bytes())
    if inspection['extra_rows']!=expected['extra_rows']:raise AssertionError('Unexpected extra-construct row set')
    with tempfile.TemporaryDirectory() as directory:
        archive=n['run_unified']({source.name:source.read_bytes()},directory)[0]
        with zipfile.ZipFile(archive) as z:
            if any(name.endswith(('_v3.1.xlsx','_EC_upload.xlsx')) for name in z.namelist()):raise AssertionError('Normal outputs must not exist for Summit')
            filename=next(name for name in z.namelist() if name.endswith('_DNA_constructs.xlsx'))
            w=openpyxl.load_workbook(io.BytesIO(z.read(filename)),read_only=True,data_only=True)
            fallback=list(w.active.iter_rows(min_row=2,values_only=True));w.close()
    with reference.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    result=compare(rows,fallback)
    if len(rows)!=expected['constructs']:raise AssertionError('Registered reference construct count changed')
    result.update(source_sha256=expected['source_sha256'],reference_sha256=expected['reference_sha256'],notebook_sha256=hashlib.sha256(notebook.read_bytes()).hexdigest(),version='2.03')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('reference',type=Path);parser.add_argument('--notebook',type=Path,default=ROOT/'Twist_Unified_Intake_Converter_v2.03.ipynb');parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    report=check(args.source,args.reference,args.notebook);args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2));raise SystemExit(0 if report['status']=='passed' else 1)
