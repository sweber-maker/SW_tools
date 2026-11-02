import io, sys, unittest, zipfile, tempfile
from pathlib import Path
from lxml import etree as ET
from openpyxl import Workbook, load_workbook
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from convert import convert, run_batch, TEMPLATE, Q

def source():
    w=Workbook(); s=w.active; s.title='Antibody Designs'
    s['C4']='Example'; s['G4']='KAPPA'; s['H4']='Heavy'; s['R4']='Light'; s['V4']='ACTG'
    d=w.create_sheet('Order Details'); d.append(['Order Details','Selection','Notes'])
    d.append(['Scale','HT IgG 4 mL Purified','Keep this note'])
    d.append(['Pooling',None]); d.append(['Cell Line','CHO'])
    d.append(['Additional Requests','Special request'])
    b=io.BytesIO(); w.save(b); return b.getvalue()

class ConverterTests(unittest.TestCase):
    def test_values_and_blank_order_fields(self):
        content,n,issues=convert(source()); self.assertEqual(n,1)
        w=load_workbook(io.BytesIO(content),data_only=False)
        self.assertEqual(w['Sequence']['C4'].value,'Example')
        self.assertEqual(w['Sequence']['S4'].value,'ACTG')
        self.assertEqual(w['Order Details']['B3'].value,'HT IgG 4 mL Purified')
        self.assertEqual(w['Order Details']['C3'].value,'Keep this note')
        self.assertEqual(w['Order Details']['B5'].value,'CHO')
        self.assertEqual(w['Order Details']['B17'].value,'Special request')
        for r in [4,6,7,8,9,10,11,12,13,14,15,16]: self.assertIsNone(w['Order Details'].cell(r,2).value)
    def test_template_parts_and_styles(self):
        content,_,_=convert(source())
        with zipfile.ZipFile(TEMPLATE) as original, zipfile.ZipFile(io.BytesIO(content)) as output:
            self.assertEqual(set(original.namelist()),set(output.namelist()))
            for name in original.namelist():
                if not name.startswith('xl/worksheets/') or not name.endswith('.xml'):
                    self.assertEqual(original.read(name),output.read(name),name)
                else:
                    before=ET.fromstring(original.read(name)); after=ET.fromstring(output.read(name))
                    for tag in ['cols','mergeCells','sheetViews','pageMargins','pageSetup','conditionalFormatting']:
                        self.assertEqual([ET.tostring(e) for e in before.findall(Q(tag))],[ET.tostring(e) for e in after.findall(Q(tag))],name+tag)
                    self.assertFalse(any(ET.QName(e).localname=='dataValidation' and e.get('type')=='list' for e in after.iter()))
                    for c in before.iter(Q('c')):
                        other=after.find(f".//{Q('c')}[@r='{c.get('r')}']")
                        self.assertEqual(c.get('s'),other.get('s'))
    def test_download_names(self):
        with tempfile.TemporaryDirectory() as d:
            paths=run_batch({'My upload.xlsx':source()},d)
            self.assertEqual(paths[0].name,'My upload_converted_v1.02.zip')
            with zipfile.ZipFile(paths[0]) as z:
                self.assertTrue(all(n.startswith('My upload_converted_v1.02') for n in z.namelist()))
                self.assertIsNone(z.testzip())
    def test_missing_designs(self):
        w=Workbook(); b=io.BytesIO(); w.save(b)
        with self.assertRaisesRegex(ValueError,'Missing Antibody'): convert(b.getvalue())

if __name__=='__main__': unittest.main()
