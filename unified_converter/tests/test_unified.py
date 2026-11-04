import base64, contextlib, csv, io, json, sys, tempfile, types, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import openpyxl
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import load_engine, NOTEBOOK
N=load_engine()

def pack(w):
    out=io.BytesIO();w.save(out);w.close();return out.getvalue()

def v42(chains=2,pur='Protein A',count=2,settings=False):
    w=openpyxl.Workbook();s=w.active;s.title='Antibody Designs'
    s.cell(3,15,'Construct 1 Sequence (DNA or AA)')
    for i in range(count):
        r=i+4
        for col,val in {1:2,2:'B'+str(i+1),3:f'Example_{i}',4:pur,7:'hIgG2' if chains==2 else 'VHH',8:'KAPPA' if chains==2 else 'N/A',9:f'Example_{i}_VH',10:'custom VH vector',11:'Contained In Insert Sequence',12:'GCCACC',13:'Contained In Insert Sequence',14:'ATGAAA',15:'ATGAAACCCGGG'}.items():s.cell(r,col,val)
        if chains==2:
            for col,val in {16:f'Example_{i}_VL',17:'custom VL vector',18:'Contained In Insert Sequence',19:'GCCACC',20:'Contained In Insert Sequence',21:'ATGCCC',22:'ATGCCCAAATTT'}.items():s.cell(r,col,val)
    d=w.create_sheet('Antibody Settings');d.append(['Antibody Customizations']);d.append(['Order Details','Selection','Notes']);d.append(['Scale*','1mL Purified' if settings else None]);d.append(['Cell Line*','CHO' if settings else None])
    return pack(w)

def paired_csv(records=None):
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['IgG Name','Construct Name (DNA)','Insert Sequence (DNA)','Vector Name','Plate (fixed plate maps)','Well (fixed plate maps)','Product Type'])
    for row in records or [('Pair','Pair_VL','ATGCCC','vector L','2','B3','IgG'),('Pair','Pair_VH','ATGAAA','vector H','2','B3','IgG')]:writer.writerow(row)
    return out.getvalue().encode('utf-8-sig')

def legacy():
    w=openpyxl.Workbook();s=w.active;s.title='Sequence Download';s.append(['IgG Name','VH Name','VH (VDJ) Sequence (DNA or AA)','VL Name','VL Sequence (DNA or AA)','IgG Isotype']);s.append(['Old','Old_VH','ATGAAA','Old_VL','ATGCCC','hIgG2']);return pack(w)

def workbook(content):return openpyxl.load_workbook(io.BytesIO(content),data_only=True)

class UnifiedTests(unittest.TestCase):
    def test_embedded_archives(self):
        with zipfile.ZipFile(io.BytesIO(N['EC_TEMPLATES'])) as z:
            self.assertIsNone(z.testzip());self.assertEqual(len(z.namelist()),12)
            for name in z.namelist():
                with self.subTest(template=name):
                    w=workbook(z.read(name));self.assertIn('Data entry',w.sheetnames);w.close()
        w=workbook(N['V42_TEMPLATE']);self.assertIn('Antibody Designs',w.sheetnames);w.close()

    def check_flavor(self, chains, pur, label, container):
        content,notes,meta=N['convert_bytes'](v42(chains,pur),f'input {container}.xlsx',N['EC_TEMPLATES'])
        self.assertEqual((meta['rows'],meta['constructs'],meta['purification'],meta['container']),(2,chains,label,container))
        w=workbook(content);s=w['Data entry'];h={N['norm'](c.value):c.column for c in s[3] if c.value}
        self.assertEqual(s.cell(4,h['vhvdjsequencednaoraa']).value,'ATGAAACCCGGG')
        if chains==2:self.assertEqual(s.cell(4,h['vlsequencednaoraa']).value,'ATGCCCAAATTT')
        self.assertEqual(s.cell(5,h['iggname']).value,'Example_1');w.close()

    def test_route_v42(self):
        kind,out=N['process_one'](v42(),'input.xlsx')
        self.assertEqual(kind,'v42');self.assertEqual([r[0] for r in out],['EC','v3.1']);self.assertEqual([r[2] for r in out],[2,2])

    def test_route_csv(self):
        kind,out=N['process_one'](paired_csv(),'paired.csv')
        self.assertEqual(kind,'sequence_download');self.assertEqual([r[0] for r in out],['EC','v4.2','v3.1'])
        for label,content,count,issues,notes in out:
            self.assertEqual(count,1)
            w=workbook(content)
            if label=='v4.2':self.assertEqual((w['Antibody Designs']['O4'].value,w['Antibody Designs']['V4'].value),('ATGAAA','ATGCCC'))
            w.close()

    def test_route_legacy(self):
        kind,out=N['process_one'](legacy(),'old.xlsx');self.assertEqual(kind,'sequence_download');self.assertEqual(len(out),3)

    def test_route_ec(self):
        ec,_,_=N['convert_bytes'](v42(),'input.xlsx',N['EC_TEMPLATES'])
        kind,out=N['process_one'](ec,'ec.xlsx');self.assertEqual(kind,'ec');self.assertEqual(out[0][0],'v4.2')
        w=workbook(out[0][1]);self.assertEqual(w['Antibody Designs']['O4'].value,'ATGAAACCCGGG');self.assertEqual(w['Antibody Designs']['V4'].value,'ATGCCCAAATTT');w.close()

    def test_csv_pairs_by_role_not_row_order(self):
        rows,_=N['parse_csv_rows'](paired_csv());self.assertEqual([c['sequence'] for c in rows[0]['chains']],['ATGAAA','ATGCCC'])

    def test_csv_missing_headers(self):
        with self.assertRaisesRegex(ValueError,'missing'):N['parse_csv_rows'](b'name,sequence\na,ATG\n')

    def test_csv_missing_partner(self):
        with self.assertRaisesRegex(ValueError,'exactly one VH and one VL'):N['parse_csv_rows'](paired_csv([('a','a_VH','ATG','','','','')]))

    def test_csv_duplicate_chain(self):
        with self.assertRaisesRegex(ValueError,'multiple VH'):N['parse_csv_rows'](paired_csv([('a','a_VH','ATG','','','',''),('a','a_VH2','ATG','','','','')]))

    def test_csv_ambiguous_role(self):
        with self.assertRaisesRegex(ValueError,'uniquely'):N['parse_csv_rows'](paired_csv([('a','unknown','ATG','','','','')]))

    def test_csv_inconsistent_well(self):
        with self.assertRaisesRegex(ValueError,'inconsistent'):N['parse_csv_rows'](paired_csv([('a','a_VH','ATG','','1','A1',''),('a','a_VL','ATG','','1','B1','')]))

    def test_csv_empty(self):
        data=paired_csv().decode('utf-8-sig').splitlines()[0].encode()
        with self.assertRaisesRegex(ValueError,'No paired'):N['parse_csv_rows'](data)

    def test_invalid_extension(self):
        with self.assertRaisesRegex(ValueError,'Only'):N['kind_from_source'](b'x','input.txt')

    def test_corrupt_workbook(self):
        with self.assertRaises(zipfile.BadZipFile):N['kind_from_source'](b'bad','input.xlsx')

    def test_unrecognized_workbook(self):
        with self.assertRaisesRegex(ValueError,'Cannot find'):N['kind_from_source'](pack(openpyxl.Workbook()),'input.xlsx')

    def test_empty_designs(self):
        with self.assertRaisesRegex(ValueError,'No antibody'):N['process_one'](v42(count=0),'input.xlsx')

    def test_extra_construct_rejected(self):
        w=workbook(v42());w['Antibody Designs']['AD4']='ATG'
        with self.assertRaisesRegex(ValueError,'unsupported'):N['process_one'](pack(w),'input.xlsx')

    def test_mixed_chains_rejected(self):
        w=workbook(v42());w['Antibody Designs']['V5']=None
        with self.assertRaisesRegex(ValueError,'Mixed one- and two-chain'):N['process_one'](pack(w),'input.xlsx')

    def test_mixed_purification_rejected(self):
        w=workbook(v42());w['Antibody Designs']['D5']='Nickel'
        with self.assertRaisesRegex(ValueError,'Mixed purification'):N['process_one'](pack(w),'input.xlsx')

    def test_dropdown_match_preserves_custom(self):
        self.assertEqual(N['match_dropdown']('custom vector',['one','two']),('custom vector','verbatim'))
        self.assertEqual(N['match_dropdown'](' HEK-293 ',['HEK293','CHO']),('HEK293','normalized'))

    def test_validation_detects_wrong_count(self):
        content,_,_=N['convert_v3'](v42())
        with self.assertRaisesRegex(AssertionError,'Expected 7'):N['validate_workbook'](content,7,'v3.1')

    def test_more_than_96_rows(self):
        content,_,meta=N['convert_bytes'](v42(count=100),'input.xlsx',N['EC_TEMPLATES'])
        self.assertEqual(meta['rows'],100)
        w=openpyxl.load_workbook(io.BytesIO(content));s=w['Data entry'];h={N['norm'](c.value):c.column for c in s[3] if c.value};self.assertEqual(s.cell(103,h['iggname']).value,'Example_99')
        rules=[d for d in s.data_validations.dataValidation if any(r.min_row==4 for r in d.sqref.ranges)]
        self.assertTrue(rules);self.assertTrue(all(any(r.max_row>=103 for r in d.sqref.ranges if r.min_row==4) for d in rules));w.close()

# These are ordinary failing regression tests: failures must remain visible in the report.
class RequirementRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob,_,_=N['convert_v3'](v42(settings=True));cls.w=workbook(cls.blob)
    @classmethod
    def tearDownClass(cls):cls.w.close()

    def test_v3_retains_template_tabs(self):
        self.assertEqual(self.w.sheetnames,['READ ME','Contact Information','Sequence','Order Details','Additional Service Requests','Sheet3'])
    def test_v3_keeps_template_instruction_row(self):
        self.assertEqual(self.w['Sequence']['A1'].value,'V3.1')
    def test_v3_order_scale_from_source(self):self.assertEqual(self.w['Order Details']['B3'].value,'HT IgG 1 mL Purified')
    def test_v3_order_cell_line_from_source(self):self.assertEqual(self.w['Order Details']['B5'].value,'CHO')
    def test_v3_order_unoccupied_stays_blank(self):self.assertIsNone(self.w['Order Details']['B4'].value)
    def test_v3_isotype_preserved(self):self.assertEqual(self.w['Sequence']['D3'].value,'hIgG2')
    def test_v3_plate_well_preserved(self):self.assertEqual((self.w['Sequence']['A3'].value,self.w['Sequence']['B3'].value),('2','B1'))
    def test_v3_custom_kozak_sequence_preserved(self):
        w=workbook(v42());w['Antibody Designs']['L4']='GCCACCATG'
        out,_,_=N['convert_v3'](pack(w));r=workbook(out);self.assertEqual(r['Sequence']['I3'].value,'GCCACCATG');r.close()
    def test_ec_roundtrip_plate_preserved(self):
        ec,_,_=N['convert_bytes'](v42(),'input.xlsx',N['EC_TEMPLATES']);w=workbook(ec);rows,_=N['parse'](w);w.close()
        self.assertEqual(str(rows[0]['plate']),'2')
    def test_csv_partial_row_must_not_silently_disappear(self):
        data=paired_csv()+b'Broken,Broken_VH,,,,,\n'
        with self.assertRaises(ValueError):N['parse_csv_rows'](data)
    def test_histidine_tag_length_counts_both_codons(self):
        w=workbook(v42(chains=1,pur='Nickel'));w['Antibody Designs']['F4']='CACCATCACCATCACCAT'
        content,_,_=N['convert_bytes'](pack(w),'input.xlsx',N['EC_TEMPLATES'])
        out=workbook(content);sheet=out['Data entry'];h={N['norm'](c.value):c.column for c in sheet[3] if c.value}
        self.assertEqual(sheet.cell(4,h['histaglength']).value,6);out.close()

    def test_named_design_missing_sequence_is_not_silently_skipped(self):
        w=workbook(v42());w['Antibody Designs']['O5']=None
        with self.assertRaises(ValueError):N['process_one'](pack(w),'input.xlsx')

    def test_underscore_tube_filename_selects_tube(self):
        _,_,meta=N['convert_bytes'](v42(),'input_tube.xlsx',N['EC_TEMPLATES'])
        self.assertEqual(meta['container'],'tube')


class BatchTests(unittest.TestCase):
    def batch(self,uploads):
        with tempfile.TemporaryDirectory() as directory:
            original=zipfile.ZipFile
            def redirected(path,*args,**kwargs):
                if isinstance(path,str) and path.startswith('/content/'):path=str(Path(directory)/Path(path).name)
                return original(path,*args,**kwargs)
            bridge=types.SimpleNamespace(ZipFile=redirected,ZIP_DEFLATED=zipfile.ZIP_DEFLATED)
            def fake(blob,name):
                if blob==b'bad':raise ValueError('bad input')
                return 'v42',[('EC',b'workbook fixture',1,[],'')]
            with patch.dict(N,{'zipfile':bridge,'process_one':fake}),contextlib.redirect_stdout(io.StringIO()):
                path=N['run_unified'](uploads)
            with original(Path(directory)/Path(path).name) as z:
                self.assertIsNone(z.testzip());return path,z.namelist(),z.read('conversion_report.csv').decode('utf-8-sig')
    def test_batch_continues_after_bad_input(self):
        _,names,report=self.batch({'bad.xlsx':b'bad','good.xlsx':b'good'});self.assertIn('good_EC.xlsx',names);self.assertIn('ERROR',report);self.assertIn('OK',report)
    def test_case_insensitive_collision_reported(self):
        _,names,report=self.batch({'A.xlsx':b'good','a.xlsx':b'good'});self.assertIn('collision',report)
    def test_archive_has_original_filename_and_version(self):
        path,_,_=self.batch({'Customer.xlsx':b'good'});self.assertIn('Customer',Path(path).name);self.assertIn('converted',Path(path).name)
    def test_outputs_have_version_suffix(self):
        _,names,_=self.batch({'Customer.xlsx':b'good'});self.assertIn('Customer_converted_v2.0_EC.xlsx',names)

# Separate test IDs give each EC template its own outcome.
for chains in (1,2):
    for pur,label in [('Protein A','protein-a'),('Nickel','nickel'),('None','none')]:
        for container in ('plate','tube'):
            def test(self,chains=chains,pur=pur,label=label,container=container):
                self.check_flavor(chains,pur,label,container)
            setattr(UnifiedTests,f'test_flavor_{chains}chain_{label.replace("-","_")}_{container}',test)

if __name__=='__main__':unittest.main()
