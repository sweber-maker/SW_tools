import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_summit_reference import compare

class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.insert='ATGAAACCC';self.construct='GGGG'+self.insert+'TTTT'
        self.rows=[{'Name':'Example','Vector name':'pVector','Insertion point name':'NotI_XbaI','Insert sequence':self.insert,'Construct sequence':self.construct,'Insert length':str(len(self.insert)),'Construct length':str(len(self.construct)),'Vector length':'10'}]
        self.source=[('Example',self.insert,'Empty Vector - pVector-NotI_XbaI')]
    def test_matches_insert_not_whole_construct(self):
        self.assertNotEqual(self.insert,self.construct);self.assertEqual(compare(self.rows,self.source)['status'],'passed')
    def test_modified_insert_fails(self):
        self.rows[0]['Insert sequence']='ATGAAACCA';self.assertEqual(compare(self.rows,self.source)['status'],'failed')
    def test_wrong_site_fails(self):
        self.rows[0]['Insertion point name']='EcoRI_XbaI';self.assertEqual(compare(self.rows,self.source)['checks']['vector_site_matches'],0)
    def test_duplicate_insert_in_full_construct_fails(self):
        self.rows[0]['Construct sequence']=self.construct+self.insert;self.rows[0]['Construct length']=str(len(self.construct+self.insert))
        result=compare(self.rows,self.source);self.assertEqual(result['checks']['insert_occurs_once'],0);self.assertEqual(result['status'],'failed')
    def test_changed_name_fails(self):
        self.rows[0]['Name']='Other';self.assertFalse(compare(self.rows,self.source)['checks']['same_name_set'])
    def test_bad_length_fails(self):
        self.rows[0]['Insert length']='8';self.assertEqual(compare(self.rows,self.source)['status'],'failed')
    def test_duplicate_names_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):compare(self.rows*2,self.source)
    def test_missing_columns_rejected(self):
        with self.assertRaisesRegex(ValueError,'columns'):compare([{'Name':'Example'}],self.source)

if __name__=='__main__':unittest.main()
