import base64, importlib.util, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch

class UITests(unittest.TestCase):
    def load_ui(self):
        self.callbacks={}
        colab=types.ModuleType('google.colab')
        colab.output=types.SimpleNamespace(register_callback=self.callbacks.__setitem__)
        with patch.dict(sys.modules,{'google.colab':colab}):
            spec=importlib.util.spec_from_file_location('colab_ui',Path(__file__).parents[1]/'ui/colab_ui.py')
            ui=importlib.util.module_from_spec(spec); spec.loader.exec_module(ui)
        return ui

    def test_upload_callback_download_and_failure(self):
        ui=self.load_ui();calls=[]
        with tempfile.TemporaryDirectory() as directory:
            def converter(uploaded,out):
                calls.append(uploaded)
                path=Path(out)/'sample_converted_v1.03.zip';path.write_bytes(b'zip content');return [path]
            with patch.object(ui,'display') as rendered:
                callback=ui.show_converter(converter,directory)
            markup=rendered.call_args.args[0].data
            self.assertIn('multiple hidden',markup)
            self.assertIn("event.dataTransfer.files",markup)
            self.assertNotIn('__CALLBACK__',markup)
            result=self.callbacks[callback]('sample.xlsx',base64.b64encode(b'input').decode()).data
            self.assertEqual(result['name'],'sample_converted_v1.03.zip')
            self.assertEqual(base64.b64decode(result['data']),b'zip content')
            self.assertEqual(calls,[{'sample.xlsx':b'input'}])
            self.assertIn('error',ui.convert_upload('wrong.txt','',converter,directory))
            self.assertIn('error',ui.convert_upload('bad.xlsx','???',converter,directory))
