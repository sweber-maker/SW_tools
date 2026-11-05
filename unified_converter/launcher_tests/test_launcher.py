import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import types
import unittest
from unittest.mock import patch
import urllib.error
import zipfile
import nbformat
import openpyxl  # Load optional NumPy support before mocking sys.modules.

ROOT=Path(__file__).resolve().parents[1]
NOTEBOOK=ROOT.parent/'START_HERE.ipynb'
DATA=json.loads(NOTEBOOK.read_text())
DESCRIPTOR=DATA['metadata']['sw_tools']
VERSION=DESCRIPTOR['version']
PACKAGE=(ROOT/'releases'/DESCRIPTOR['bundle_filename']).read_bytes()
CODE=''.join(DATA['cells'][1]['source'])

class LauncherTests(unittest.TestCase):
    def setUp(self):self.directories=[]
    def tearDown(self):
        for directory in self.directories:shutil.rmtree(directory,ignore_errors=True)
    def execute(self,payload=PACKAGE,code=CODE,side_effect=None):
        callbacks={};colab=types.ModuleType('google.colab')
        colab.output=types.SimpleNamespace(register_callback=callbacks.__setitem__)
        namespace={}
        with patch.dict(sys.modules,{'google.colab':colab}),patch('urllib.request.urlopen',side_effect=side_effect,return_value=io.BytesIO(payload)) as fetch,patch('subprocess.run') as install,patch('IPython.display.display') as display,patch('IPython.display.clear_output'),contextlib.redirect_stdout(io.StringIO()):
            try:exec(compile(code,'START_HERE.ipynb','exec'),namespace)
            finally:
                if 'work_dir' in namespace:self.directories.append(namespace['work_dir'])
        return namespace,callbacks,fetch,install,display
    def test_notebook_schema(self):nbformat.validate(nbformat.read(NOTEBOOK,as_version=4))
    def test_notebook_small_and_lines_short(self):
        self.assertLess(NOTEBOOK.stat().st_size,20000);self.assertLess(max(map(len,CODE.splitlines())),300)
        self.assertNotIn('RELEASE_SOURCES',CODE)
    def test_root_and_versioned_notebook_identical(self):
        self.assertEqual(NOTEBOOK.read_bytes(),(ROOT/f'Twist_Unified_Intake_Converter_v{VERSION}.ipynb').read_bytes())
    def test_package_hash_and_manifest(self):
        self.assertEqual(hashlib.sha256(PACKAGE).hexdigest(),DESCRIPTOR['bundle_sha256'])
        with zipfile.ZipFile(io.BytesIO(PACKAGE)) as z:
            self.assertIsNone(z.testzip());manifest=json.loads(z.read('manifest.json'))
            self.assertEqual(manifest['version'],VERSION)
            for name,digest in manifest['files'].items():self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest)
    def test_expected_runtime_sources_are_embedded(self):
        old=json.loads((ROOT/'Twist_Unified_Intake_Converter_v2.03.ipynb').read_text())
        tree=ast.parse(''.join(old['cells'][1]['source']))
        literals={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('RELEASE_SOURCES','RUNTIME_SOURCE')}
        with zipfile.ZipFile(io.BytesIO(PACKAGE)) as z:
            current=json.loads(z.read('sources.json'))
            if 'signals' in current:
                self.assertEqual(current['signals'],(ROOT/'signals_v2_05.py').read_text())
                self.assertEqual(current['ec_engine'],(ROOT/'ec_engine_v2_05.py').read_text())
                self.assertEqual(current['v3_engine'],(ROOT/'v3_engine_v2_05.py').read_text().replace("VERSION = '2.05'","VERSION = '"+VERSION+"'",1))
                if 'intake' in current:
                    self.assertEqual(current['intake'],(ROOT/'intake_v2_06.py').read_text())
                    self.assertEqual(current['routing'],(ROOT/'routing_v2_06.py').read_text())
                    self.assertEqual(z.read('runtime.py').decode(),(ROOT/'runtime_v2_06.py').read_text())
                    del current['intake'];current['routing']=literals['RELEASE_SOURCES']['routing']
                else:self.assertEqual(z.read('runtime.py').decode(),(ROOT/('runtime_v2_06.py' if 'intake' in current else 'runtime_v2_05.py')).read_text())
                if 'intake' in current:
                    self.assertEqual(current['intake'],(ROOT/'intake_v2_06.py').read_text())
                    self.assertEqual(current['routing'],(ROOT/'routing_v2_06.py').read_text())
                    del current['intake'];current['routing']=literals['RELEASE_SOURCES']['routing']
                # Remaining template assets and extra-construct rules remain frozen.
                del current['signals']
                current['v3_engine']=literals['RELEASE_SOURCES']['v3_engine']
                current['ec_engine']=literals['RELEASE_SOURCES']['ec_engine']
            else:
                current['v3_engine']=current['v3_engine'].replace("VERSION = '"+VERSION+"'","VERSION = '2.03'",1)
                self.assertEqual(z.read('runtime.py').decode(),literals['RUNTIME_SOURCE'])
            current['routing']=current['routing'].replace('VERSION = "'+VERSION+'"','VERSION = "2.03"',1)
            self.assertEqual(current,literals['RELEASE_SOURCES'])
    def test_real_startup_registers_upload_controls(self):
        namespace,callbacks,fetch,install,display=self.execute()
        self.assertEqual(namespace['_engine']['VERSION'],VERSION);self.assertEqual(len(callbacks),1)
        fetch.assert_called_once_with(DESCRIPTOR['bundle_url'],timeout=30)
        self.assertTrue(install.call_args.kwargs['check']);self.assertIn('openpyxl==3.1.5',install.call_args.args[0])
        markup=display.call_args.args[0].data
        self.assertIn('dataTransfer.files',markup);self.assertIn('multiple hidden',markup);self.assertIn('Version '+VERSION,markup)
    def test_checksum_failure_blocks_start(self):
        with self.assertRaisesRegex(ValueError,'did not match'):self.execute(payload=b'not the converter')
    def test_network_failure_is_not_silent(self):
        with self.assertRaises(urllib.error.HTTPError):self.execute(side_effect=urllib.error.HTTPError(DESCRIPTOR['bundle_url'],404,'not found',{},None))
    def test_invalid_extraction_path_rejected(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:z.writestr('../outside.py','bad')
        payload=data.getvalue();code=CODE.replace(DESCRIPTOR['bundle_sha256'],hashlib.sha256(payload).hexdigest())
        with self.assertRaisesRegex(ValueError,'package path'):self.execute(payload=payload,code=code)
    def test_restart_uses_fresh_ui(self):
        _,a,_,_,_=self.execute();_,b,_,_,_=self.execute();self.assertNotEqual(set(a),set(b))

if __name__=='__main__':unittest.main()
