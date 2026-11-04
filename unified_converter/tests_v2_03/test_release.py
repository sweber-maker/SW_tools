import ast,importlib.util,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
import openpyxl
from lxml import etree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine import load_engine
NOTEBOOK=ROOT/'Twist_Unified_Intake_Converter_v2.03.ipynb';N=load_engine(NOTEBOOK)
spec=importlib.util.spec_from_file_location('v202_checks_for_current',ROOT/'tests_v2_02/test_release.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
old.N=N;old.NOTEBOOK=NOTEBOOK;old.previous.N=N;old.previous.shared.N=N
v42,pack,workbook=old.v42,old.pack,old.workbook
AssemblyTests=old.AssemblyTests
V3RegressionTests=old.V3RegressionTests
RemainingKnownTests=old.RemainingKnownTests
UIStatusTests=old.UIStatusTests
class RouteAndECTests(old.RouteAndECTests):
    def test_mixed_chains_rejected(self):
        # 2.03 deliberately supports mixed 1/2-chain inputs by splitting EC outputs.
        w=workbook(v42());w['Antibody Designs']['V5']=None;w['Antibody Designs']['P5']=None
        _,outputs=N['process_one'](pack(w),'input.xlsx')
        self.assertEqual([o[0] for o in outputs],['EC_upload_1chain','EC_upload_2chain','v3.1'])
        self.assertEqual([o[2] for o in outputs],[1,1,2])
class ExtraConstructTests(old.ExtraConstructTests):
    def test_release_naming(self):
        items,_=self.bundle(v42());self.assertTrue(all(k.startswith('Source upload_converted_v2.03') for k in items));self.assertTrue(any(k.endswith('_EC_upload.xlsx') for k in items))
    def test_embedded_sources_match(self):
        tree=ast.parse(''.join(json.loads(NOTEBOOK.read_text())['cells'][1]['source']))
        values={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('RELEASE_SOURCES','RUNTIME_SOURCE')}
        for key,file in [('constructs','constructs_v2_02.py'),('routing','routing_v2_03.py'),('v3_engine','v3_engine_v2_03.py')]:self.assertEqual(values['RELEASE_SOURCES'][key],(ROOT/file).read_text())
        self.assertEqual(values['RUNTIME_SOURCE'],(ROOT/'runtime_v2_03.py').read_text())
class CustomerFindingTests(unittest.TestCase):
    def convert_setting(self,label,value,note=None):
        w=workbook(v42());s=w['Antibody Settings'];s.delete_rows(1,s.max_row);s.append([label,value,note])
        output,count,issues=N['convert_v3'](pack(w));return workbook(output),issues
    def test_no_physical_shipment_cross_field_mapping(self):
        w,_=self.convert_setting('Shipping Container* (select Scale for options)','No physical shipment','Source shipping note')
        self.assertIsNone(w['Order Details']['B12'].value);self.assertEqual(w['Order Details']['B15'].value,'No physical shipment');self.assertEqual(w['Order Details']['C15'].value,'Source shipping note');w.close()
    def test_yes_sterile_filtration(self):
        w,_=self.convert_setting('Post Purification Sterile Filtration','Yes');self.assertEqual(w['Order Details']['B10'].value,'Post Purification Sterile Filtration');w.close()
    def test_no_sterile_filtration(self):
        w,_=self.convert_setting('Post Purification Sterile Filtration','No');self.assertIsNone(w['Order Details']['B10'].value);w.close()
    def test_negative_sterile_phrase_not_mapped_to_affirmative(self):
        w,_=self.convert_setting('Post Purification Sterile Filtration','No sterile filtration');self.assertIsNone(w['Order Details']['B10'].value);w.close()
    def test_four_ml_not_one_point_four_ml(self):
        w,_=self.convert_setting('Shipping Container* (select Scale for options)','4 mL Micronic Tubes - tubes come with barcodes and plate map')
        self.assertTrue(w['Order Details']['B12'].value.startswith('4mL'));w.close()
    def test_existing_v31_normalization(self):
        blob,_,_=N['convert_v3'](v42());self.assertEqual(N['kind_from_source'](blob,'existing.xlsx'),'v31')
        _,outputs=N['process_one'](blob,'existing.xlsx');self.assertEqual([o[0] for o in outputs],['v3.1']);self.assertEqual(outputs[0][2],2)
    def test_bad_source_style_is_repaired(self):
        blob,_,_=N['convert_v3'](v42());out=io.BytesIO();q=lambda x:'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'+x
        with zipfile.ZipFile(io.BytesIO(blob)) as source,zipfile.ZipFile(out,'w') as dest:
            for entry in source.infolist():
                value=source.read(entry.filename)
                if entry.filename=='xl/worksheets/sheet3.xml':
                    root=ET.fromstring(value);root.find(f".//{q('c')}[@r='C4']").set('s','999999');value=ET.tostring(root)
                dest.writestr(entry,value)
        fixed,count,_=N['convert_v3'](out.getvalue());w=workbook(fixed);self.assertEqual(w['Sequence']['C4'].value,'Example_0');self.assertEqual(count,2);w.close()
    def test_existing_services_preserved(self):
        blob,_,_=N['convert_v3'](v42());w=workbook(blob);w['Additional Service Requests']['B3']='Yes';w['Additional Service Requests']['C3']='Service note'
        fixed,_,_=N['convert_v3'](pack(w));w=workbook(fixed)
        self.assertEqual(w['Additional Service Requests']['B3'].value,'Yes');self.assertEqual(w['Additional Service Requests']['C3'].value,'Service note');w.close()
