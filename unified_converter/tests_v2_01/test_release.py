import ast, base64, importlib.util, io, json, sys, tempfile, unittest, zipfile
from pathlib import Path
from lxml import etree as ET
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine import load_engine
NOTEBOOK=ROOT/'Twist_Unified_Intake_Converter_v2.01.ipynb'
N=load_engine(NOTEBOOK)
spec=importlib.util.spec_from_file_location('baseline_checks_for_release',ROOT/'tests/test_unified.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared);shared.N=N
v42,pack,paired_csv,workbook=shared.v42,shared.pack,shared.paired_csv,shared.workbook
# Reuse all 34 EC/route tests against this release's embedded engines.
RouteAndECTests=shared.UnifiedTests
Q=lambda tag:'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'+tag

class V3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob,cls.count,cls.issues=N['convert_v3'](v42(settings=True));cls.w=workbook(cls.blob)
    @classmethod
    def tearDownClass(cls):cls.w.close()
    def test_template_tabs(self):
        self.assertEqual(self.w.sheetnames,['READ ME','Contact Information','Sequence','Order Details','Additional Service Requests','Sheet3'])
    def test_instruction_rows_and_first_design(self):
        self.assertEqual(self.w['Sequence']['A1'].value,'V3.1')
        self.assertEqual(self.w['Sequence']['C2'].value,'IgG Name')
        self.assertIn('Note:',self.w['Sequence']['C3'].value)
        self.assertEqual(self.w['Sequence']['C4'].value,'Example_0')
    def test_scale_from_source(self):self.assertEqual(self.w['Order Details']['B3'].value,'HT IgG 1 mL Purified')
    def test_cell_line_from_source(self):self.assertEqual(self.w['Order Details']['B5'].value,'CHO')
    def test_unoccupied_fields_stay_blank(self):
        for r in (4,6,7,8,9,10,11,12,13,14,15,16,17):
            self.assertIsNone(self.w['Order Details'].cell(r,2).value)
    def test_isotype_preserved(self):self.assertEqual(self.w['Sequence']['D4'].value,'hIgG2')
    def test_plate_well_preserved(self):
        self.assertEqual((self.w['Sequence']['A4'].value,self.w['Sequence']['B4'].value),('2','B1'))
    def test_custom_kozak_and_leader_preserved(self):
        w=workbook(v42())
        for address,value in {'L4':'GCCACCATG','N4':'ATGRYSWKMBDHVN','S4':'gCcaccATG','U4':'MRLLLAAAA'}.items():w['Antibody Designs'][address]=value
        out,_,issues=N['convert_v3'](pack(w));w=workbook(out)
        for address,value in {'I4':'GCCACCATG','K4':'ATGRYSWKMBDHVN','P4':'gCcaccATG','R4':'MRLLLAAAA'}.items():self.assertEqual(w['Sequence'][address].value,value)
        self.assertTrue(any('custom sequence' in issue['status'] for issue in issues));w.close()
    def test_styles_and_package_preserved(self):
        with zipfile.ZipFile(ROOT/'templates/v3.1.xlsx') as before,zipfile.ZipFile(io.BytesIO(self.blob)) as after:
            self.assertEqual(before.namelist(),after.namelist())
            for name in before.namelist():
                if not (name.startswith('xl/worksheets/') and name.endswith('.xml')):
                    self.assertEqual(before.read(name),after.read(name),name);continue
                a,b=ET.fromstring(before.read(name)),ET.fromstring(after.read(name))
                for tag in ('cols','mergeCells','sheetViews','pageMargins','pageSetup','conditionalFormatting'):
                    self.assertEqual([ET.tostring(e) for e in a.findall(Q(tag))],[ET.tostring(e) for e in b.findall(Q(tag))],name+tag)
                for cell in a.iter(Q('c')):
                    other=b.find(f".//{Q('c')}[@r='{cell.get('r')}']")
                    self.assertIsNotNone(other);self.assertEqual(cell.get('s'),other.get('s'))
                self.assertFalse(any(ET.QName(e).localname=='dataValidation' and e.get('type')=='list' for e in b.iter()))
    def test_reordered_labels_notes_and_missing_choices(self):
        w=workbook(v42());s=w['Antibody Settings'];s.delete_rows(1,s.max_row)
        s.append(['Shipping Container* (select Scale for options)','96-well Deep-well Plate - comes with plate map','Pack carefully'])
        s.append(['Buffer Exchange',None,'Note without a selection'])
        s.append(['Scale*','8mL Purified'])
        s.append(['Pooling',None])
        s.append(['Additional Requests','Review this request'])
        out,_,_=N['convert_v3'](pack(w));r=workbook(out);s=r['Order Details']
        self.assertEqual(s['B3'].value,'HT IgG 8 mL Purified')
        self.assertEqual(s['C12'].value,'Pack carefully');self.assertIsNone(s['B8'].value)
        self.assertEqual(s['C8'].value,'Note without a selection');self.assertIsNone(s['B4'].value)
        self.assertEqual(s['B17'].value,'Review this request');r.close()
    def test_all_purified_scales(self):
        for amount in (1,2,3,4,8,16,24,32):
            with self.subTest(amount=amount):
                w=workbook(v42());w['Antibody Settings']['B3']=f'{amount}mL Purified'
                out,_,_=N['convert_v3'](pack(w));r=workbook(out)
                self.assertEqual(''.join(r['Order Details']['B3'].value.split()),f'HTIgG{amount}mLPurified');r.close()
    def test_no_settings_tab_means_no_defaults(self):
        w=workbook(v42());del w['Antibody Settings']
        out,_,issues=N['convert_v3'](pack(w));r=workbook(out)
        self.assertTrue(all(r['Order Details'].cell(row,2).value is None for row in range(3,18)))
        self.assertTrue(any('absent' in issue['status'] for issue in issues));r.close()
    def test_placeholder_selection_stays_blank(self):
        w=workbook(v42());w['Antibody Settings']['B3']='PLEASE SELECT OPTION FROM DROPDOWN MENU'
        out,_,_=N['convert_v3'](pack(w));r=workbook(out);self.assertIsNone(r['Order Details']['B3'].value);r.close()
    def test_custom_vectors_are_not_weak_fuzzy_matches(self):
        w=workbook(v42());w['Antibody Designs']['J4']='custom VH vector';w['Antibody Designs']['Q4']='custom VL vector'
        out,_,issues=N['convert_v3'](pack(w));r=workbook(out)
        self.assertEqual(r['Sequence']['G4'].value,'custom VH vector');self.assertEqual(r['Sequence']['N4'].value,'custom VL vector');r.close()
    def test_named_design_without_sequence_rejected(self):
        w=workbook(v42());w['Antibody Designs']['O5']=None
        with self.assertRaisesRegex(ValueError,'no construct 1 sequence'):N['process_one'](pack(w),'input.xlsx')
    def test_csv_to_v3_has_blank_order_details_and_both_chains(self):
        _,outputs=N['process_one'](paired_csv(),'paired.csv')
        r=workbook(next(blob for label,blob,*_ in outputs if label=='v3.1'))
        self.assertEqual((r['Sequence']['L4'].value,r['Sequence']['S4'].value),('ATGAAA','ATGCCC'))
        self.assertTrue(all(r['Order Details'].cell(row,2).value is None for row in range(3,18)));r.close()
    def test_contacts_come_from_source(self):
        w=workbook(v42());s=w.create_sheet('Contact Information')
        for row,label,value in [(4,'First Name','Shipping person'),(5,'Last Name','Shipping surname'),(18,'First Name','Billing person'),(19,'Last Name','Billing surname')]:s.cell(row,1,label);s.cell(row,2,value)
        out,_,_=N['convert_v3'](pack(w));r=workbook(out)
        self.assertEqual(r['Contact Information']['B4'].value,'Shipping person');self.assertEqual(r['Contact Information']['B18'].value,'Billing person');r.close()
    def test_example_mini_binder_policy_is_reported(self):
        w=workbook(v42(chains=1));w['Antibody Designs']['G4']='mini-binder'
        out,_,issues=N['convert_v3'](pack(w));r=workbook(out)
        self.assertEqual(r['Sequence']['D4'].value,'hIgG1 VHH Fc Fusion')
        self.assertTrue(any('mini-binder mapping' in issue['status'] for issue in issues));r.close()
    def test_unknown_isotype_never_becomes_a_different_igg_subclass(self):
        w=workbook(v42());w['Antibody Designs']['G4']='hIgG3'
        out,_,issues=N['convert_v3'](pack(w));r=workbook(out)
        self.assertEqual(r['Sequence']['D4'].value,'Other, please specify below')
        self.assertTrue(any(issue['original']=='hIgG3' for issue in issues));r.close()
    def test_completion_cache_updates(self):
        self.assertTrue(self.w['Order Details']['D3'].value)
        self.assertFalse(self.w['Order Details']['D8'].value)

class ReleaseTests(unittest.TestCase):
    def test_filename_and_report_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=N['run_unified']({'My upload.xlsx':v42()},directory)[0]
            self.assertEqual(archive.name,'My upload_converted_v2.01.zip')
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip());self.assertTrue(all(name.startswith('My upload_converted_v2.01') for name in z.namelist()))
                self.assertIn('2.01',z.read('My upload_converted_v2.01_report.csv').decode('utf-8-sig'))
    def test_notebook_embeds_reviewed_sources(self):
        notebook=json.loads(NOTEBOOK.read_text());tree=ast.parse(''.join(notebook['cells'][1]['source']))
        values={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('RELEASE_SOURCES','RUNTIME_SOURCE')}
        self.assertEqual(values['RELEASE_SOURCES']['v3_engine'],(ROOT/'v3_engine.py').read_text())
        self.assertEqual(values['RELEASE_SOURCES']['routing'],(ROOT/'routing_v2_01.py').read_text())
        self.assertEqual(values['RUNTIME_SOURCE'],(ROOT/'runtime_v2_01.py').read_text())
        self.assertEqual(base64.b64decode(values['RELEASE_SOURCES']['v3_template']),(ROOT/'templates/v3.1.xlsx').read_bytes())
        self.assertEqual(notebook['cells'][1]['metadata']['cellView'],'form')
        self.assertIn('dataTransfer.files',''.join(notebook['cells'][1]['source']))

class RemainingKnownTests(unittest.TestCase):
    # Keep unrelated known failures visible, not skipped or marked expected failures.
    test_csv_partial_row_must_not_silently_disappear=shared.RequirementRegressionTests.test_csv_partial_row_must_not_silently_disappear
    test_histidine_tag_length_counts_both_codons=shared.RequirementRegressionTests.test_histidine_tag_length_counts_both_codons
    test_underscore_tube_filename_selects_tube=shared.RequirementRegressionTests.test_underscore_tube_filename_selects_tube
