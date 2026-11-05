import io,json,sys,unittest,zipfile
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine import load_engine
from signals_v2_05 import resolve,dna,instruction,prepare
N=load_engine(ROOT/'Twist_Unified_Intake_Converter_v2.05.ipynb')
DEFAULT='ATGAGAGCCTGGATCTTTTTCCTGCTGTGCCTGGCTGGGCGCGCCCTGGCC'
MENU='Twist Vector: Leader fully contained in insert, replace this dropdown with SEQUENCE'
K='GCCGCCACC'

def source(value=MENU,setting='Twist Sequence',insert='EVQLVESGGGLVQPGGSLRLSCAAS',candidates=(DEFAULT,),vl=DEFAULT):
    w=openpyxl.Workbook();s=w.active;s.title='Antibody Designs'
    s.cell(3,15,'Construct 1 Sequence (DNA or AA)')
    fields={3:'Example',4:'Protein A',7:'hIgG1',8:'LAMBDA',9:'Example_VH',10:'pTwist CMV hIgG1-HuIgG1Fc_TAG',11:'Twist Sequence',12:K,13:setting,14:value,15:insert,16:'Example_VL',17:'pTwist CMV hIgL2-Lambda_TAG',18:'Twist Sequence',19:K,20:'Twist Sequence',21:vl,22:'DIQMTQSPSSLSASVGDRVTITC'}
    for col,value in fields.items():
        if value is not None:s.cell(4,col,value)
    choices=w.create_sheet('Dropdown Lists');choices.append(['Leader Sequence','PLEASE SELECT OPTION FROM DROPDOWN MENU'])
    for candidate in candidates:choices.append([None,candidate])
    choices.append([None,MENU]);choices.append(['Kozak Sequence',K])
    out=io.BytesIO();w.save(out);w.close();return out.getvalue()

def ec_values(blob):
    content,notes,meta=N['convert_bytes'](blob,'example.xlsx',N['EC_TEMPLATES']);w=openpyxl.load_workbook(io.BytesIO(content),data_only=True)
    s=w['Data entry'];h={N['norm'](c.value):c.column for c in s[3] if c.value}
    result={key:s.cell(4,col).value for key,col in h.items()};w.close();return result,meta

class SignalTests(unittest.TestCase):
    def test_explicit_twist_setting_uses_source_dna_for_aa_insert(self):
        value,note=resolve(MENU,'Twist Sequence',K,'EVQLVESGG',[DEFAULT]);self.assertEqual(value,DEFAULT);self.assertIn('explicit',note)
    def test_custom_setting_does_not_guess_default_for_aa_insert(self):
        value,note=resolve(MENU,'Fully Contained In Custom Vector',K,'EVQLVESGG',[DEFAULT]);self.assertIsNone(value);self.assertIn('unresolved',note)
    def test_exact_insert_dna_prefix_can_resolve_known_leader(self):
        value,note=resolve(MENU,'Contained In Insert Sequence',K,K+DEFAULT+'ATGTAA',[DEFAULT]);self.assertEqual(value,DEFAULT);self.assertIn('exact known DNA',note)
    def test_internal_match_is_not_leader_evidence(self):
        value,_=resolve(MENU,None,K,'ATGTAA'+DEFAULT,[DEFAULT]);self.assertIsNone(value)
    def test_ambiguous_source_definitions_do_not_pick_first(self):
        value,_=resolve(MENU,'Twist Sequence',K,'EVQLVESGG',[DEFAULT,'ATGAAATTT']);self.assertIsNone(value)
    def test_no_definition_does_not_invent_dna(self):
        value,_=resolve(MENU,'Twist Sequence',K,'EVQLVESGG',[]);self.assertIsNone(value)
    def test_literal_dna_takes_precedence(self):
        variant=DEFAULT[:12]+'A'+DEFAULT[13:];value,_=resolve(variant,'Twist Sequence',K,'EVQLVESGG',[DEFAULT]);self.assertEqual(value,variant)
    def test_csv_is_not_loaded_as_excel(self):
        content=b'IgG Name,Construct Name (DNA),Insert Sequence (DNA)\n';self.assertEqual(prepare(content),(content,[]))
    def test_prepare_changes_only_signal_cells(self):
        blob=source();prepared,audit=prepare(blob);self.assertNotEqual(blob,prepared);self.assertEqual(len(audit),1)
        before=openpyxl.load_workbook(io.BytesIO(blob),data_only=True);after=openpyxl.load_workbook(io.BytesIO(prepared),data_only=True)
        for row in before['Antibody Designs']:
            for cell in row:
                if cell.coordinate=='N4':self.assertEqual(after['Antibody Designs'][cell.coordinate].value,DEFAULT)
                else:self.assertEqual(after['Antibody Designs'][cell.coordinate].value,cell.value)
        before.close();after.close()
    def test_ec_replaces_menu_with_dna_and_preserves_both_aa_inserts(self):
        values,meta=ec_values(source());self.assertEqual(values['vhleadersequencedna'],DEFAULT);self.assertEqual(values['vlleadersequencedna'],DEFAULT)
        self.assertEqual(values['vhvdjsequencednaoraa'],'EVQLVESGGGLVQPGGSLRLSCAAS');self.assertEqual(values['vlsequencednaoraa'],'DIQMTQSPSSLSASVGDRVTITC')
        self.assertTrue(meta['signal_corrections'])
    def test_ec_does_not_fuzzy_change_one_base_custom_dna(self):
        variant=DEFAULT[:12]+('A' if DEFAULT[12]!='A' else 'C')+DEFAULT[13:]
        values,_=ec_values(source(value=variant));self.assertEqual(values['vhleadersequencedna'],variant)
    def test_vl_instruction_is_also_resolved(self):
        values,_=ec_values(source(value=DEFAULT,vl=MENU));self.assertEqual(values['vlleadersequencedna'],DEFAULT)
    def test_unresolved_menu_is_blank_with_review_warning(self):
        values,meta=ec_values(source(setting='Fully Contained In Custom Vector'));self.assertIsNone(values['vhleadersequencedna']);self.assertTrue(any('unresolved instruction' in text for text in meta['warnings']))
    def test_protein_signal_not_written_as_dna_or_reverse_translated(self):
        values,meta=ec_values(source(value='MKWVTFISLL'));self.assertIsNone(values['vhleadersequencedna']);self.assertTrue(any('actual DNA required' in text for text in meta['warnings']))
    def test_leader_dna_across_all_twelve_ec_templates(self):
        for chains in (1,2):
            for purification,expected in [('Protein A','protein-a'),('Nickel','nickel'),('None','none')]:
                for container in ('plate','tube'):
                    with self.subTest(chains=chains,purification=purification,container=container):
                        w=openpyxl.load_workbook(io.BytesIO(source()));s=w['Antibody Designs'];s['D4']=purification
                        if chains==1:
                            s['G4']='hIgG1 VHH Fc Fusion'
                            for col in range(16,23):s.cell(4,col).value=None
                        out=io.BytesIO();w.save(out);w.close()
                        content,notes,meta=N['convert_bytes'](out.getvalue(),f'example {container}.xlsx',N['EC_TEMPLATES'])
                        w=openpyxl.load_workbook(io.BytesIO(content),data_only=True);s=w['Data entry'];h={N['norm'](c.value):c.column for c in s[3] if c.value}
                        self.assertEqual(s.cell(4,h['vhleadersequencedna']).value,DEFAULT)
                        self.assertEqual((meta['constructs'],meta['purification'],meta['container']),(chains,expected,container));w.close()
    def test_v3_normalization_concentration_label(self):
        w=openpyxl.load_workbook(io.BytesIO(source()));settings=w.create_sheet('Antibody Settings');settings.append(['Scale*','1mL Purified']);settings.append(['Normalization','0.5 mg/mL ']);out=io.BytesIO();w.save(out);w.close()
        content,_,_=N['convert_v3'](out.getvalue());w=openpyxl.load_workbook(io.BytesIO(content),data_only=True)
        self.assertEqual(w['Order Details']['B9'].value,'0.5 mg/mL Normalization');w.close()
    def test_paired_csv_route_survives_signal_correction(self):
        blob=b'IgG Name,Construct Name (DNA),Insert Sequence (DNA)\nExample,Example_VH,ATGAAA\nExample,Example_VL,ATGCCC\n'
        kind,outputs=N['process_one'](blob,'paired.csv');self.assertEqual([item[0] for item in outputs],['EC_upload','v4.2','v3.1'])
    def test_v3_receives_same_resolved_leader(self):
        content,_,issues=N['convert_v3'](source());w=openpyxl.load_workbook(io.BytesIO(content),data_only=True);self.assertEqual(w['Sequence']['K4'].value,DEFAULT);w.close()
        self.assertTrue(any('explicit Twist' in item['status'] for item in issues))

if __name__=='__main__':unittest.main()
