import ast, csv, importlib.util, io, json, sys, tempfile, unittest, zipfile
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine import load_engine
NOTEBOOK=ROOT/'Twist_Unified_Intake_Converter_v2.02.ipynb';N=load_engine(NOTEBOOK)
spec=importlib.util.spec_from_file_location('previous_release_checks',ROOT/'tests_v2_01/test_release.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
previous.N=N;previous.shared.N=N
v42,pack,workbook,paired_csv=previous.v42,previous.pack,previous.workbook,previous.paired_csv
V3RegressionTests=previous.V3Tests
RemainingKnownTests=previous.RemainingKnownTests
spec=importlib.util.spec_from_file_location('construct_checks',ROOT/'constructs_v2_02.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
K='GCCACC';L='ATGAAACCCGGGTTT';BODY='GATCTAGATCTAGAC'

def extra_blob(count=3,mixed=False,missing_name=False):
    w=workbook(v42(count=2 if mixed else 1));s=w['Antibody Designs']
    target=5 if mixed else 4
    if missing_name:s.cell(target,3).value=None;s.cell(target,15).value=None
    for index,(start,end) in enumerate(C.BLOCKS,1):
        if index>count:continue
        values={start:f'Gene_{index}',start+1:f'Vector_{index}',start+3:K,start+5:L,end:K+L+BODY}
        for col,value in values.items():s.cell(target,col+1,value)
    if missing_name:s.cell(target,3).value=None;s.cell(target,15).value=None
    return pack(w)

class RouteAndECTests(previous.shared.UnifiedTests):
    def test_route_v42(self):
        kind,out=N['process_one'](v42(),'input.xlsx');self.assertEqual(kind,'v42');self.assertEqual([r[0] for r in out],['EC_upload','v3.1'])
    def test_route_csv(self):
        kind,out=N['process_one'](paired_csv(),'paired.csv');self.assertEqual(kind,'sequence_download');self.assertEqual([r[0] for r in out],['EC_upload','v4.2','v3.1'])
    def test_route_legacy(self):
        kind,out=N['process_one'](previous.shared.legacy(),'old.xlsx');self.assertEqual(kind,'sequence_download');self.assertEqual([r[0] for r in out],['EC_upload','v4.2','v3.1'])

class AssemblyTests(unittest.TestCase):
    def check(self,k,l,s,expected):
        result,action,warnings=C.assemble_dna(k,l,s);self.assertEqual(result,expected);return action,warnings
    def test_already_complete(self):self.check(K,L,K+L+BODY,K+L+BODY)
    def test_no_components_in_insert(self):self.check(K,L,BODY,K+L+BODY)
    def test_leader_already_in_insert(self):self.check(K,L,L+BODY,K+L+BODY)
    def test_kozak_already_in_insert(self):self.check(K,L,K+BODY,K+L+BODY)
    def test_five_prime_overhang_preserved(self):self.check(K,L,'GAATTC'+K+L+BODY,'GAATTC'+K+L+BODY)
    def test_leader_field_already_has_kozak(self):self.check(K,K+L,BODY,K+L+BODY)
    def test_leader_field_has_kozak_and_insert_has_kozak(self):self.check(K,K+L,K+BODY,K+L+BODY)
    def test_lowercase_whitespace_normalized(self):self.check('gcc acc','atg aaa ccc ggg ttt','gat cta gat cta gac',K+L+BODY)
    def test_only_kozak_supplied(self):self.check(K,None,BODY,K+BODY)
    def test_only_leader_supplied(self):self.check(None,L,L+BODY,L+BODY)
    def test_missing_components_reported(self):
        _,warnings=self.check(None,None,BODY,BODY);self.assertEqual(len(warnings),2)
    def test_one_base_overlap_is_not_trimmed(self):self.check('GCCACC','CTGAAATTT',BODY,'GCCACCCTGAAATTT'+BODY)
    def test_existing_multiple_prefixes_not_deleted(self):
        _,warnings=self.check(K,L,K+L+BODY+K+L,K+L+BODY+K+L);self.assertTrue(warnings)
    def test_internal_kozak_is_not_used_to_edit_gene(self):
        with self.assertRaisesRegex(ValueError,'internally'):C.assemble_dna(K,L,BODY+K+BODY)
    def test_reversed_components_fail(self):
        with self.assertRaisesRegex(ValueError,'internally'):C.assemble_dna(K,L,L+K+BODY)
    def test_partial_leader_fails(self):
        with self.assertRaisesRegex(ValueError,'partial Leader'):C.assemble_dna(K,L,L[:12]+BODY)
    def test_partial_kozak_fails(self):
        with self.assertRaisesRegex(ValueError,'partial Kozak'):C.assemble_dna('GCCGCCACC',L,'GCCACC'+BODY)
    def test_protein_insert_fails(self):
        with self.assertRaisesRegex(ValueError,'DNA'):C.assemble_dna(K,L,'MKWVTFISLLFLFSSAYS')
    def test_protein_leader_fails(self):
        with self.assertRaisesRegex(ValueError,'DNA'):C.assemble_dna(K,'MKWVTFISLL',BODY)
    def test_ambiguous_nucleotides_fail(self):
        with self.assertRaisesRegex(ValueError,'DNA'):C.assemble_dna(K,L,'ATGNNNTAA')
    def test_rna_fails(self):
        with self.assertRaisesRegex(ValueError,'DNA'):C.assemble_dna(K,L,'AUGAAAUAA')
    def test_formula_fails(self):
        with self.assertRaisesRegex(ValueError,'DNA'):C.assemble_dna(K,L,'="ATG"')
    def test_single_component_internal_match_requires_review(self):
        with self.assertRaisesRegex(ValueError,'internally'):C.assemble_dna(K,None,BODY+K+BODY)
    def test_internal_kozak_does_not_prevent_missing_five_prime_kozak(self):
        _,warnings=self.check(K,L,L+BODY+K+BODY,K+L+BODY+K+BODY);self.assertTrue(warnings)
    def test_missing_insert_fails(self):
        with self.assertRaisesRegex(ValueError,'missing'):C.assemble_dna(K,L,None)

class ExtraConstructTests(unittest.TestCase):
    def test_three_construct_standard_routes_all_reject(self):
        blob=extra_blob()
        for label,call in [('process_one',lambda:N['process_one'](blob,'input.xlsx')),('v3',lambda:N['convert_v3'](blob)),('EC',lambda:N['convert_bytes'](blob,'input.xlsx',N['EC_TEMPLATES'])),('router',lambda:N['convert_routed'](blob,'input.xlsx',N['EC_TEMPLATES'],N['V42_TEMPLATE']))]:
            with self.subTest(route=label),self.assertRaises(N['ExtraConstructError']):call()
    def test_fourth_only_also_rejects(self):
        w=workbook(v42());w['Antibody Designs']['AK4']='ATGAAA'
        with self.assertRaises(N['ExtraConstructError']):N['process_one'](pack(w),'input.xlsx')
    def test_extra_row_without_antibody_or_first_sequence_rejects(self):
        with self.assertRaises(N['ExtraConstructError']):N['process_one'](extra_blob(missing_name=True),'input.xlsx')
    def test_extra_name_without_sequence_rejects(self):
        w=workbook(v42());w['Antibody Designs']['X5']='Extra name'
        with self.assertRaises(N['ExtraConstructError']):N['convert_bytes'](pack(w),'input.xlsx',N['EC_TEMPLATES'])
    def test_normalized_three_chain_input_rejects(self):
        rows,_=N['parse_csv_rows'](paired_csv());rows[0]['chains'].append(rows[0]['chains'][0].copy())
        with self.assertRaises(N['ExtraConstructError']):N['convert_to_v42'](rows,'input.xlsx',N['V42_TEMPLATE'])
    def bundle(self,blob):
        with tempfile.TemporaryDirectory() as d:
            archive=N['run_unified']({'Source upload.xlsx':blob},d)[0]
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip());items={name:z.read(name) for name in z.namelist()}
        report=list(csv.DictReader(io.StringIO(next(v for k,v in items.items() if k.endswith('_report.csv')).decode('utf-8-sig'))))
        return items,report
    def test_three_construct_fallback(self):
        items,report=self.bundle(extra_blob())
        self.assertEqual([r['Status'] for r in report],['REJECTED','REJECTED','OK'])
        self.assertFalse(any(k.endswith(('_v3.1.xlsx','_EC_upload.xlsx')) for k in items))
        w=workbook(next(v for k,v in items.items() if k.endswith('_DNA_constructs.xlsx')));s=w.active
        self.assertEqual(list(s.values),[('Name','Sequence','Vector Name')]+[(f'Gene_{i}',K+L+BODY,f'Vector_{i}') for i in range(1,4)]);w.close()
    def test_four_construct_fallback(self):
        items,report=self.bundle(extra_blob(count=4));self.assertEqual(report[-1]['Rows'],'4')
    def test_mixed_workbook_entirely_uses_fallback(self):
        items,report=self.bundle(extra_blob(mixed=True));self.assertEqual(report[-1]['Rows'],'5');self.assertEqual(report[0]['Status'],'REJECTED')
    def test_invalid_dna_no_partial_table(self):
        w=workbook(extra_blob());w['Antibody Designs']['AD4']='MKWVTFISLL'
        items,report=self.bundle(pack(w));self.assertEqual(report[-1]['Status'],'FAILED');self.assertFalse(any(k.endswith('.xlsx') for k in items))
        audit=json.loads(next(v for k,v in items.items() if k.endswith('_audit.json')));self.assertTrue(audit['errors'])
    def test_fallback_reports_missing_components(self):
        w=workbook(extra_blob());w['Antibody Designs']['AA4']=None
        items,report=self.bundle(pack(w));self.assertEqual(report[-1]['Status'],'REVIEW')
    def test_good_file_still_converts_after_bad_file(self):
        with tempfile.TemporaryDirectory() as d:
            files=N['run_unified']({'bad.xlsx':b'bad','good.xlsx':v42()},d);self.assertEqual(len(files),2)
            with zipfile.ZipFile(files[1]) as z:self.assertTrue(any(k.endswith('_EC_upload.xlsx') for k in z.namelist()))
    def test_ratio_declaring_missing_construct_fails_fallback(self):
        w=workbook(extra_blob());w['Antibody Designs']['W4']='1:1:1:1'
        items,report=self.bundle(pack(w));self.assertEqual(report[-1]['Status'],'FAILED')
    def test_placeholder_extra_fields_do_not_trigger(self):
        w=workbook(v42());w['Antibody Designs']['Z4']='PLEASE SELECT OPTION FROM DROPDOWN MENU'
        _,outputs=N['process_one'](pack(w),'input.xlsx');self.assertEqual([out[0] for out in outputs],['EC_upload','v3.1'])
    def test_export_does_not_execute_formula_like_names(self):
        w=workbook(extra_blob());w['Antibody Designs']['X4']='=1+1'
        items,_=self.bundle(pack(w));w=openpyxl.load_workbook(io.BytesIO(next(v for k,v in items.items() if k.endswith('_DNA_constructs.xlsx'))))
        self.assertEqual(w.active['A4'].value,'=1+1');self.assertEqual(w.active['A4'].data_type,'s');w.close()
    def test_audit_tracks_no_duplicate_prefix(self):
        items,_=self.bundle(extra_blob());audit=json.loads(next(v for k,v in items.items() if k.endswith('_audit.json')))
        self.assertTrue(all('already present' in item['action'] for item in audit['constructs']))
    def test_release_naming(self):
        items,_=self.bundle(v42());self.assertTrue(all(k.startswith('Source upload_converted_v2.02') for k in items));self.assertTrue(any(k.endswith('_EC_upload.xlsx') for k in items))
    def test_two_construct_ratio_is_not_misclassified(self):
        w=workbook(v42());w['Antibody Designs']['W4']='1:1'
        _,outputs=N['process_one'](pack(w),'input.xlsx');self.assertEqual([out[0] for out in outputs],['EC_upload','v3.1'])
    def test_duplicate_names_preserved_and_flagged(self):
        w=workbook(extra_blob());w['Antibody Designs']['X4']='Gene_1'
        items,report=self.bundle(pack(w));self.assertEqual(report[-1]['Status'],'REVIEW')
        r=workbook(next(v for k,v in items.items() if k.endswith('_DNA_constructs.xlsx')))
        self.assertEqual(r.active.max_row,4);r.close()
    def test_unresolved_extra_formula_is_not_ignored(self):
        w=workbook(v42());w['Antibody Designs']['AD4']='="ATGAAA"'
        with self.assertRaises(N['ExtraConstructError']):N['process_one'](pack(w),'input.xlsx')
    def test_cached_extra_dna_is_detected(self):
        from lxml import etree as ET
        w=workbook(v42());w['Antibody Designs']['AD4']='="ATGAAA"';blob=pack(w)
        out=io.BytesIO();q=lambda tag:'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'+tag
        with zipfile.ZipFile(io.BytesIO(blob)) as source,zipfile.ZipFile(out,'w') as dest:
            for entry in source.infolist():
                data=source.read(entry.filename)
                if entry.filename=='xl/worksheets/sheet1.xml':
                    root=ET.fromstring(data);cell=root.find(f".//{q('c')}[@r='AD4']");cell.set('t','str');cell.find(q('v')).text='ATGAAA';data=ET.tostring(root)
                dest.writestr(entry,data)
        with self.assertRaises(N['ExtraConstructError']):N['process_one'](out.getvalue(),'input.xlsx')
    def test_embedded_sources_match(self):
        n=json.loads(NOTEBOOK.read_text());tree=ast.parse(''.join(n['cells'][1]['source']))
        literal={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('RELEASE_SOURCES','RUNTIME_SOURCE')}
        for key,path in [('constructs','constructs_v2_02.py'),('routing','routing_v2_02.py'),('v3_engine','v3_engine_v2_02.py')]:self.assertEqual(literal['RELEASE_SOURCES'][key],(ROOT/path).read_text())
        self.assertEqual(literal['RUNTIME_SOURCE'],(ROOT/'runtime_v2_02.py').read_text())
        self.assertIn('dataTransfer.files',''.join(n['cells'][1]['source']))

class UIStatusTests(unittest.TestCase):
    def load_ui(self):
        import types
        from unittest.mock import patch
        colab=types.ModuleType('google.colab');colab.output=types.SimpleNamespace(register_callback=lambda *args:None)
        with patch.dict(sys.modules,{'google.colab':colab}):
            spec=importlib.util.spec_from_file_location('release_ui',ROOT/'ui_v2_02/colab_ui.py')
            ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)
        return ui
    def test_fallback_is_labeled_as_rejected_normal_conversion(self):
        import base64
        with tempfile.TemporaryDirectory() as d:
            result=self.load_ui().convert_upload('source.xlsx',base64.b64encode(extra_blob()).decode(),N['run_unified'],d)
            self.assertIn('Normal conversions rejected',result['message']);self.assertIn('DNA-only fallback',result['message'])
    def test_failed_dna_is_not_labeled_ready(self):
        import base64
        w=workbook(extra_blob());w['Antibody Designs']['AD4']='PROTEIN'
        with tempfile.TemporaryDirectory() as d:
            result=self.load_ui().convert_upload('source.xlsx',base64.b64encode(pack(w)).decode(),N['run_unified'],d)
            self.assertIn('Conversion failed',result['message']);self.assertIn('no incomplete DNA table',result['message'])
