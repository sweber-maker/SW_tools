import csv,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine import load_engine
from intake_v2_06 import identify,normalize
N=load_engine(ROOT/'Twist_Unified_Intake_Converter_v2.06.ipynb')
DEFAULT='ATGAGAGCCTGGATCTTTTTCCTGCTGTGCCTGGCTGGGCGCGCCCTGGCC'
HEADERS=['Plate #','Well','IGG Name','Purification','His Tag Selection','His Tag Sequence','IGG Isotype','Light Chain (LAMBDA or KAPPA)','VH Name','VH Vector Name - Insertion Site Name','VH Kozak Settings','VH Kozak Sequence (DNA)','VH Leader Setting','VH Leader Sequence (DNA)','VH (VDJ) Sequence (DNA or AA)','VL Name','VL Vector Name - Insertion Site Name','VL Kozak Settings (DNA)','VL Kozak Sequence (DNA)','VL Leader Setting','VL Leader Sequence (DNA)','VL Sequence (DNA or AA) ']
def pack(workbook):
    out=io.BytesIO();workbook.save(out);workbook.close();return out.getvalue()
def source():
    w=openpyxl.Workbook();s=w.active;s.title='Sequence';s.append(HEADERS)
    s.append([None,None,'Example','Protein A',None,None,'hIgG1','KAPPA','Example_VH','pTwist CMV hIgG1-HuIgG1Fc_TAG','Twist Sequence','GCCGCCACC','Twist Sequence',DEFAULT,'EVQLVESGGGLVQPGGSLRLSCAAS','Example_VL','pTwist CMV hIgK-Kappa_TAG','Twist Sequence','GCCGCCACC','Twist Sequence',DEFAULT,'DIQMTQSPSSLSASVGDRVTITC'])
    return pack(w)
class IntakeTests(unittest.TestCase):
    def test_detects_by_headers_not_filename(self):
        blob=source();self.assertEqual(N['kind_from_source'](blob,'anything.xlsx'),'sequence_intake')
    def test_only_ec_output(self):
        kind,outputs=N['process_one'](source(),'anything.xlsx');self.assertEqual(kind,'sequence_intake');self.assertEqual([o[0] for o in outputs],['EC_upload'])
    def test_all_source_values_map_to_same_v42_positions(self):
        blob=source();converted,is_new=normalize(blob);self.assertTrue(is_new)
        original=openpyxl.load_workbook(io.BytesIO(blob),data_only=True);canonical=openpyxl.load_workbook(io.BytesIO(converted),data_only=True)
        self.assertEqual(list(original['Sequence'].iter_rows(min_row=2,max_col=22,values_only=True))[0],list(canonical['Antibody Designs'].iter_rows(min_row=4,max_row=4,max_col=22,values_only=True))[0])
        original.close();canonical.close()
    def test_reordered_columns_are_not_silently_misread(self):
        w=openpyxl.load_workbook(io.BytesIO(source()));s=w['Sequence'];s['N1'],s['O1']=s['O1'].value,s['N1'].value
        with self.assertRaisesRegex(ValueError,'column layout'):N['process_one'](pack(w),'reordered.xlsx')
    def test_existing_v42_table_keeps_priority(self):
        canonical,_=normalize(source());w=openpyxl.load_workbook(io.BytesIO(canonical));del w['__sw_tools_input']
        table=w.create_sheet('Sequence');table.append(HEADERS)
        self.assertEqual(N['kind_from_source'](pack(w),'existing.xlsx'),'v42')
    def test_normalization_is_idempotent(self):
        blob,_=normalize(source());again,flag=normalize(blob);self.assertTrue(flag);self.assertEqual(again,blob)
    def test_legacy_six_column_sequence_download_unchanged(self):
        w=openpyxl.Workbook();s=w.active;s.title='Sequence Download';s.append(['IgG Name','VH Name','VH (VDJ) Sequence (DNA or AA)','VL Name','VL Sequence (DNA or AA)','IgG Isotype']);s.append(['Legacy','VH','ATGAAA','VL','ATGCCC','hIgG1'])
        self.assertEqual(N['kind_from_source'](pack(w),'legacy.xlsx'),'sequence_download')
    def test_v31_not_misclassified(self):
        w=openpyxl.Workbook();s=w.active;s.title='Sequence';s['A1']='V3.1';s['C2']='IgG Name';blob=pack(w);self.assertEqual(N['kind_from_source'](blob,'v31.xlsx'),'v31')
    def test_names_aa_and_dna_signals_preserved(self):
        _,outputs=N['process_one'](source(),'anything.xlsx');w=openpyxl.load_workbook(io.BytesIO(outputs[0][1]),data_only=True);s=w['Data entry'];h={N['norm'](c.value):c.column for c in s[3] if c.value}
        for field,value in [('iggname','Example'),('vhname','Example_VH'),('vlname','Example_VL'),('vhvdjsequencednaoraa','EVQLVESGGGLVQPGGSLRLSCAAS'),('vlsequencednaoraa','DIQMTQSPSSLSASVGDRVTITC'),('vhleadersequencedna',DEFAULT),('vlleadersequencedna',DEFAULT)]:self.assertEqual(s.cell(4,h[field]).value,value)
        w.close()
    def test_missing_primary_does_not_disappear(self):
        w=openpyxl.load_workbook(io.BytesIO(source()));w['Sequence']['O2']=None
        with self.assertRaisesRegex(ValueError,'no VH sequence'):N['process_one'](pack(w),'missing.xlsx')
    def test_named_light_chain_without_sequence_is_not_discarded(self):
        w=openpyxl.load_workbook(io.BytesIO(source()));w['Sequence']['V2']=None
        with self.assertRaisesRegex(ValueError,'no VL sequence'):N['process_one'](pack(w),'missing_vl.xlsx')
    def test_missing_name_does_not_disappear(self):
        w=openpyxl.load_workbook(io.BytesIO(source()));w['Sequence']['C2']=None
        with self.assertRaisesRegex(ValueError,'no antibody name'):N['process_one'](pack(w),'missing.xlsx')
    def test_extra_construct_rejects_normal_conversion(self):
        w=openpyxl.load_workbook(io.BytesIO(source()));w['Sequence']['X2']='Third';w['Sequence']['AD2']='ATGAAA'
        with self.assertRaises(N['ExtraConstructError']):N['process_one'](pack(w),'extra.xlsx')
    def test_three_construct_fallback_uses_original_source_rows(self):
        w=openpyxl.load_workbook(io.BytesIO(source()));s=w['Sequence']
        for col in (15,22):s.cell(2,col,'GCCGCCACC'+DEFAULT+'ATGAAA')
        for col,value in {24:'Third',25:'pVector',27:'GCCGCCACC',29:DEFAULT,30:'GCCGCCACC'+DEFAULT+'ATGTAA'}.items():s.cell(2,col,value)
        with tempfile.TemporaryDirectory() as d:
            archive=N['run_unified']({'extra.xlsx':pack(w)},d)[0]
            with zipfile.ZipFile(archive) as z:
                self.assertFalse(any(name.endswith(('_EC_upload.xlsx','_v3.1.xlsx','_v4.2.xlsx')) for name in z.namelist()))
                audit=json.loads(z.read(next(name for name in z.namelist() if name.endswith('_audit.json'))))
                self.assertEqual(audit['extra_construct_rows'],[2]);self.assertTrue(all(row['source_row']==2 for row in audit['constructs']))
                self.assertTrue(any(name.endswith('_DNA_constructs.xlsx') for name in z.namelist()))
    def test_batch_still_converts_next_file_after_failure(self):
        with tempfile.TemporaryDirectory() as d:
            outputs=N['run_unified']({'bad.xlsx':b'bad','good.xlsx':source()},d);self.assertEqual(len(outputs),2)
            with zipfile.ZipFile(outputs[1]) as z:self.assertTrue(any(n.endswith('_EC_upload.xlsx') for n in z.namelist()));self.assertFalse(any(n.endswith(('_v3.1.xlsx','_v4.2.xlsx')) for n in z.namelist()))
    def test_versioned_archive_names_and_reports(self):
        with tempfile.TemporaryDirectory() as d:
            archive=N['run_unified']({'My input.xlsx':source()},d)[0];self.assertEqual(archive.name,'My input_converted_v2.06.zip')
            with zipfile.ZipFile(archive) as z:self.assertTrue(all(n.startswith('My input_converted_v2.06') for n in z.namelist()));self.assertIsNone(z.testzip())
    def test_diagnostics_use_original_sequence_row(self):
        w=openpyxl.load_workbook(io.BytesIO(source()));w['Sequence']['N2']='Custom Vector: Leader fully contained in insert, replace this dropdown with SEQUENCE';w['Sequence']['M2']='Fully Contained In Custom Vector'
        _,outputs=N['process_one'](pack(w),'unresolved.xlsx');self.assertTrue(any('Sequence!N2' in message for message in outputs[0][3]))

if __name__=='__main__':unittest.main()
