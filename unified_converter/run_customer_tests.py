"""Run all private real-workbook cases and package outputs without publishing customer content."""
import argparse, collections, csv, hashlib, io, json, re, sys, unittest, zipfile
from pathlib import Path
import openpyxl
from engine import load_engine
from run_tests import RecordedResult

ROOT=Path(__file__).resolve().parent
VERSION='2.03'
def norm(value):return re.sub('[^a-z0-9]','',str(value or '').lower())
def occupied(value):return value is not None and str(value).strip()!='' and 'PLEASE SELECT' not in str(value).upper()
def canonical(value):return '' if value is None else str(value).strip()
def sequence(value):return re.sub(r'\s+','',canonical(value)).upper()
def require(condition,description):
    if not condition:raise AssertionError(description)

def target_order_row(label):
    label=norm(label)
    for prefix,row in [('scale',3),('pooling',4),('cellline',5),('purificationmethod',6),('elutionbuffer',7),('bufferexchange',8),('normalization',9),('postpurificationsterilefiltration',10),('aliquot',11),('shippingcontainer',12),('customplatemap',13),('restrictionenzymesites',14),('pleaseindicateifyouprefernot',15),('shipphysicalsampleswithadditional',16),('additionalrequests',17)]:
        if label.startswith(prefix):return row
    return None

def validate_source_and_output(source,content,case):
    output=openpyxl.load_workbook(io.BytesIO(content),data_only=True)
    require(output.sheetnames==['READ ME','Contact Information','Sequence','Order Details','Additional Service Requests','Sheet3'],'v3.1 template sheet layout')
    require(output['Sequence']['A1'].value=='V3.1' and output['Sequence']['C2'].value=='IgG Name','v3.1 template instruction/header rows')
    rows=[row for row in output['Sequence'].iter_rows(min_row=4,max_col=19,values_only=True) if occupied(row[2])]
    if case['format']=='v42':
        raw=[row for row in source['Antibody Designs'].iter_rows(min_row=4,max_col=37,values_only=True) if occupied(row[2])]
        actual=[(canonical(r[2]),canonical(r[5]),sequence(r[11]),canonical(r[12]),sequence(r[18])) for r in rows]
        wanted=[(canonical(r[2]),canonical(r[8]),sequence(r[14]),canonical(r[15]),sequence(r[21])) for r in raw]
        other_pairs=[(ord(a)-65,ord(b)-65) for a,b in [('A','A'),('B','B'),('L','I'),('N','K'),('S','P'),('U','R')]]
        for original,converted in zip(raw,rows):
            for a,b in other_pairs:
                if occupied(original[a]):require(sequence(original[a])==sequence(converted[b]),'Plate/well or custom Kozak/leader preservation')
                else:require(not occupied(converted[b]),'Unset source coordinate/sequence placeholders remain unset')
    else:
        raw=[row for row in source['Sequence'].iter_rows(min_row=4,max_col=19,values_only=True) if occupied(row[2])]
        actual=[(canonical(r[2]),canonical(r[5]),sequence(r[11]),canonical(r[12]),sequence(r[18])) for r in rows]
        wanted=[(canonical(r[2]),canonical(r[5]),sequence(r[11]),canonical(r[12]),sequence(r[18])) for r in raw]
        for original,converted in zip(raw,rows):
            for col in (0,1,8,10,15,17):require(sequence(original[col])==sequence(converted[col]),'Existing v3.1 coordinates or custom sequences preserved')
        if 'Additional Service Requests' in source.sheetnames:
            for row in source['Additional Service Requests'].iter_rows(min_row=3,max_col=3):
                for cell in row[1:]:
                    if occupied(cell.value):
                        require(canonical(cell.value)==canonical(output['Additional Service Requests'][cell.coordinate].value),'Existing service selection/note preservation')
                        require(canonical(source['Additional Service Requests'].cell(cell.row,1).value)==canonical(output['Additional Service Requests'].cell(cell.row,1).value),'Service choice remains associated with the same assay/field label')
    require(len(rows)==case['designs']==len(raw),'Exact source/output design counts')
    require(actual==wanted,'Design names, chain names and both complete sequences preserved in source order')
    if 'Contact Information' in source.sheetnames:
        for r in list(range(4,16))+list(range(18,30)):
            if occupied(source['Contact Information'].cell(r,2).value):
                require(canonical(source['Contact Information'].cell(r,2).value)==canonical(output['Contact Information'].cell(r,2).value),'Source contact field preservation')
    sheet=source['Antibody Settings' if case['format']=='v42' else 'Order Details']
    expected_occupied=set();notes_count=0
    for row in sheet.iter_rows(min_row=3,max_col=3,values_only=True):
        target=target_order_row(row[0])
        if target is None:continue
        value,note=row[1:3]
        if target==12 and norm(value)=='nophysicalshipment':target=15
        actual_value=output['Order Details'].cell(target,2).value
        if occupied(value):
            expected_occupied.add(target)
            if target==3:
                amount=re.search(r'(\d+(?:\.\d+)?)\s*ml',str(value),re.I)
                if amount:require(norm(amount.group(1)+'ml') in norm(actual_value),'Scale amount preserved')
            elif target==10:
                require((norm(value) in ('yes','true') and norm(actual_value)=='postpurificationsterilefiltration') or norm(value)==norm(actual_value),'Affirmative sterile filtration mapped correctly')
            elif target==12 and 'micronic' in str(value).lower():
                src=re.search(r'(\d+(?:\.\d+)?)\s*ml',str(value),re.I);dst=re.search(r'(\d+(?:\.\d+)?)\s*ml',str(actual_value),re.I)
                require(src is not None and dst is not None and src.group(1)==dst.group(1),'Micronic container volume preserved')
            else:
                a,b=norm(value),norm(actual_value)
                require(a==b or (target==7 and a+'elutionbuffer'==b),'Source order selection matches corresponding target choice')
        if occupied(note):
            require(str(note)==str(output['Order Details'].cell(target,3).value),'Order note preserved at corresponding field');notes_count+=1
    for r in range(3,18):
        if r not in expected_occupied:require(not occupied(output['Order Details'].cell(r,2).value),'Blank source order fields stay blank')
    missing=sum(not occupied(output['Order Details'].cell(r,2).value) for r in (3,5,6,7))
    if not occupied(output['Order Details']['B12'].value) and not occupied(output['Order Details']['B15'].value):missing+=1
    output.close()
    return {'designs':len(rows),'sequence_records_verified':len(rows),'order_notes_verified':notes_count,'missing_required_order_choices':missing}

if __name__=='__main__':
    p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True);group.add_argument('--manifest',type=Path);group.add_argument('--fixtures-dir',type=Path);p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args()
    catalogue=json.loads((ROOT/'customer_cases.json').read_text())['cases']
    if args.manifest:
        locations={r['id']:Path(r['path']) for r in json.loads(args.manifest.read_text())}
    else:
        by_hash={}
        for candidate in args.fixtures_dir.rglob('*'):
            if candidate.is_file() and candidate.suffix.lower()=='.xlsx':by_hash[hashlib.sha256(candidate.read_bytes()).hexdigest()]=candidate
        locations={case['id']:by_hash[case['sha256']] for case in catalogue if case['sha256'] in by_hash}
    N=load_engine(ROOT/f'Twist_Unified_Intake_Converter_v{VERSION}.ipynb');results=[];args.output_dir.mkdir(parents=True,exist_ok=True)
    class CustomerTests(unittest.TestCase):pass
    def method(case):
        def run(self):
            source_path=locations.get(case['id']);require(source_path is not None and source_path.is_file(),'Private fixture must be supplied; absence is not a passing test')
            blob=source_path.read_bytes();require(hashlib.sha256(blob).hexdigest()==case['sha256'],'Private fixture SHA-256 matches catalogue')
            require(N['kind_from_source'](blob,case['filename'])==case['format'],'Detected input format matches independent expected format')
            inspection=N['inspect_v42'](blob);require(bool(inspection['extra_rows'])==case['extra_constructs'],'Expected extra-construct scan result')
            source=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
            try:
                path=N['run_unified']({case['filename']:blob},args.output_dir)[0]
                with zipfile.ZipFile(path) as bundle:
                    require(bundle.testzip() is None,'ZIP integrity')
                    files=bundle.namelist();require(all(name.startswith(Path(case['filename']).stem+'_converted_v'+VERSION) for name in files),'Source filename and release version on every artifact')
                    report=list(csv.DictReader(io.StringIO(bundle.read(next(name for name in files if name.endswith('_report.csv'))).decode('utf-8-sig'))))
                    require(all(row['Status']=='OK' for row in report),'No failed conversion stages')
                    v3=[name for name in files if name.endswith('_v3.1.xlsx')];require(len(v3)==1,'Exactly one v3.1 output')
                    checks=validate_source_and_output(source,bundle.read(v3[0]),case)
                    ec=[name for name in files if '_EC_upload' in name and name.endswith('.xlsx')];require(len(ec)==case['ec_workbooks'],'Expected EC output partition count')
                    expected=collections.Counter()
                    if case['format']=='v42':
                        expected=collections.Counter((canonical(r[2]),sequence(r[14]),sequence(r[21])) for r in source['Antibody Designs'].iter_rows(min_row=4,max_col=37,values_only=True) if occupied(r[2]))
                    observed=collections.Counter()
                    for name in ec:
                        wb=openpyxl.load_workbook(io.BytesIO(bundle.read(name)),data_only=True);s=wb['Data entry'];h={norm(c.value):c.column for c in s[3] if c.value}
                        for row in s.iter_rows(min_row=4,values_only=True):
                            if occupied(row[h['iggname']-1]):observed[(canonical(row[h['iggname']-1]),sequence(row[h['vhvdjsequencednaoraa']-1]),sequence(row[h['vlsequencednaoraa']-1]) if 'vlsequencednaoraa' in h else '')]+=1
                        wb.close()
                    if ec:require(observed==expected,'EC partition union retains each source design and both sequences exactly once')
                    results.append({'id':case['id'],'filename':case['filename'],'format':case['format'],'status':'passed','checks':checks,'ec_workbooks':len(ec),'extra_construct_rows':len(inspection['extra_rows']),'archive':path.name})
            finally:source.close()
        return run
    for case in catalogue:setattr(CustomerTests,'test_'+case['id'],method(case))
    result=unittest.TextTestRunner(verbosity=2,resultclass=RecordedResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(CustomerTests))
    report={'version':VERSION,'notebook_sha256':hashlib.sha256((ROOT/f'Twist_Unified_Intake_Converter_v{VERSION}.ipynb').read_bytes()).hexdigest(),'tests_run':result.testsRun,'passed':len(results),'failed':len(result.failures),'errors':len(result.errors),'cases':results,'outcomes':result.outcomes,'privacy':'No raw workbooks, sequences, contacts or customer notes stored in this report.'}
    (ROOT/f'Twist_Unified_Intake_Converter_v{VERSION}_customer_test_results.json').write_text(json.dumps(report,indent=2))
    (args.output_dir/f'Antibodies custom form v4.2_Amazon_TRKA_converted_v{VERSION}_batch_report.json').write_text(json.dumps(report,indent=2))
    sys.exit(0 if result.wasSuccessful() else 1)
