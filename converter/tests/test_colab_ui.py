import importlib.util, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch

class UITests(unittest.TestCase):
    def test_multiple_files_failure_and_retry(self):
        downloads=[]
        colab=types.ModuleType('google.colab'); colab.files=types.SimpleNamespace(download=downloads.append)
        with patch.dict(sys.modules,{'google.colab':colab}):
            spec=importlib.util.spec_from_file_location('colab_ui',Path(__file__).parents[1]/'ui/colab_ui.py')
            ui=importlib.util.module_from_spec(spec); spec.loader.exec_module(ui)
        calls=[]
        def convert(uploaded,directory):
            name=next(iter(uploaded)); calls.append(name)
            if name=='broken.xlsx': raise ValueError('Bad workbook')
            return [Path(directory)/(Path(name).stem+'_converted_v1.02.zip')]
        with patch.object(ui,'display'):
            picker,results=ui.show_converter(convert,'/tmp')
        def upload(name):
            return {'name':name,'type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','size':1,'content':memoryview(b'x'),'last_modified':__import__('datetime').datetime.now(__import__('datetime').timezone.utc)}
        picker.value=(upload('first.xlsx'),upload('broken.xlsx'),upload('second.xlsx'))
        self.assertEqual(calls,['first.xlsx','broken.xlsx','second.xlsx'])
        self.assertEqual(len(results.children),5)
        self.assertIn('Bad workbook',results.children[2].value)
        results.children[1].click()
        self.assertEqual(downloads,['/tmp/first_converted_v1.02.zip'])
        self.assertFalse(picker.disabled)
        picker.value=(upload('first.xlsx'),)
        self.assertEqual(calls[-1],'first.xlsx')
        self.assertEqual(len(calls),4)
        self.assertEqual(ui.uploaded_items({'legacy.xlsx':{'content':b'old'}}),[('legacy.xlsx',b'old')])
