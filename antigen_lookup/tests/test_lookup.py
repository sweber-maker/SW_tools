import sys, unittest, io
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quantity import calculate
from extract import extract, pack_options
from service import report, excel, batch
from openpyxl import load_workbook

HTML = '''<h1>Human IL-20, His Tag</h1><p>IL0-H5243</p>
<table><tr><th>Molecular Weight</th><td>19.4 kDa</td></tr><tr><th>Tag</th><td>His</td></tr>
<tr><th>Oligomeric State</th><td>Monomer</td></tr><tr><th>Storage</th><td>-20 C</td></tr></table>
<script type="application/ld+json">{"@type":"Product","sku":"IL0-H5243","name":"Human IL-20","offers":[{"name":"100 ug","price":"125","priceCurrency":"USD","availability":"https://schema.org/InStock"}]}</script>'''
URL='https://www.acrobiosystems.com/example-product.html'
class Tests(unittest.TestCase):
    def test_workbook_formula_and_two_runs(self):
        self.assertEqual(calculate('BLI',96,56)['Required antigen (ug)'],56)
        self.assertEqual(calculate('SPR',372,56)['Required antigen (ug)'],112)
        self.assertEqual(calculate('SPR',384,19.4)['Batches'],2)
        self.assertEqual(calculate('BLI',97,19.4)['Required antigen (ug)'],38.8)
        self.assertEqual(calculate('BLI',96,100)['Purchase target (ug)'],100)
        self.assertEqual(calculate('BLI',96,100.1)['Purchase target (ug)'],200)
    def test_assembly(self):
        self.assertEqual(calculate('BLI',96,19.4,2)['Required antigen (ug)'],38.8)
        self.assertEqual(calculate('BLI',96,38.8,2,'assembly')['Required antigen (ug)'],38.8)
        for n in [0,-1,1.5]:
            with self.assertRaises(ValueError): calculate('BLI',n,19.4)
    def test_extraction_and_missing(self):
        evidence, offers, _, _=extract(HTML,URL,'IL0-H5243')
        self.assertTrue(any(e['Value']=='19.4 kDa' for e in evidence))
        self.assertFalse(any(e['Field']=='Affinity' for e in evidence))
        options=pack_options(offers,200)
        self.assertEqual(options[0]['Total price'],'250')
        self.assertEqual(options[0]['Packs needed'],2)
        self.assertTrue(options[0]['In stock'])
        self.assertEqual(extract(HTML,URL,'OTHER')[0],[])
    def test_unknown_offers(self):
        self.assertEqual(pack_options([{'Pack / variant':'100 ug / 200 ug','Price':'100','Currency':'USD'}],100),[])
        self.assertEqual(pack_options([{'Pack / variant':'100 ug','Price':'Quote','Currency':'USD'}],100),[])
    def test_report_and_export(self):
        result=report(URL,'IL0-H5243',mw_kda=19.4,oligomer=1,html=HTML)
        self.assertEqual(result['Calculation'][0]['Purchase target (ug)'],100)
        vals={r['Field']:r['Value'] for r in result['Intake']}
        self.assertEqual(vals['Target Antigen Supplier'],'Vendor-Supplied')
        self.assertEqual(vals['Affinity'],'')
        result['Evidence'].append({'Value':'=1+1'})
        wb=load_workbook(io.BytesIO(excel(result)))
        self.assertEqual(wb['Evidence'].cell(wb['Evidence'].max_row,2).data_type,'s')
    def test_batch(self):
        with patch('service.fetch',return_value=(HTML,URL)):
            out=batch('example.csv',f'URL,Catalog,MW_kDa,Oligomer\n{URL},IL0-H5243,19.4,1\n'.encode())
        wb=load_workbook(io.BytesIO(out),data_only=True)
        self.assertIn('Purchase options',wb.sheetnames)
    def test_no_false_stock_on_error(self):
        with patch('service.fetch',side_effect=ValueError('blocked')):
            result=report(URL)
        self.assertEqual(result['Offers'],[])
        self.assertEqual(result['Calculation'],[])
if __name__=='__main__': unittest.main()
