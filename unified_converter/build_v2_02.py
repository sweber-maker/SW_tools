"""Build the self-contained, hidden-code Colab release from reviewable source files."""
import base64
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def build():
    original=json.loads((ROOT/'Twist_Unified_Intake_Converter_v2.0.ipynb').read_text())
    sources={'assets':''.join(original['cells'][2]['source']),
             'ec_engine':''.join(original['cells'][3]['source']),
             'v3_engine':(ROOT/'v3_engine_v2_02.py').read_text(),
             'routing':(ROOT/'routing_v2_02.py').read_text(),
             'constructs':(ROOT/'constructs_v2_02.py').read_text(),
             'v3_template':base64.b64encode((ROOT/'templates/v3.1.xlsx').read_bytes()).decode()}
    runtime=(ROOT/'runtime_v2_02.py').read_text()
    code='''# @title ▶ Start unified converter { display-mode: "form" }
import subprocess, sys, tempfile
from pathlib import Path
from IPython.display import clear_output
print('Preparing converter…')
try:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'openpyxl==3.1.5', 'lxml>=5,<7'], check=True, capture_output=True, text=True)
except subprocess.CalledProcessError as exc:
    raise RuntimeError('Setup failed. Reconnect the runtime and try again. ' + exc.stderr[-1500:]) from exc
'''
    code+='RELEASE_SOURCES = '+repr(sources)+'\nRUNTIME_SOURCE = '+repr(runtime)+'\n'
    code+="_runtime = {'__name__':'unified_runtime'}\nexec(RUNTIME_SOURCE, _runtime)\n_work_dir = Path(tempfile.mkdtemp(prefix='unified-2-02-'))\n_engine = _runtime['initialize'](RELEASE_SOURCES, _work_dir)\n"
    for name in ('colab_ui.py','upload.html'):
        code+=f"(_work_dir / {name!r}).write_text({(ROOT/'ui_v2_02'/name).read_text()!r})\n"
    code+="_ui = {'__name__':'unified_ui','__file__':str(_work_dir/'colab_ui.py')}\nexec((_work_dir/'colab_ui.py').read_text(), _ui)\nclear_output(wait=True)\n_controls = _ui['show_converter'](_engine['run_unified'])\n"
    compile(code,'unified-notebook','exec')
    notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'colab':{'name':'Twist Unified Intake Converter 2.02','provenance':[]}},'cells':[
        {'cell_type':'markdown','metadata':{},'source':['# Twist Unified Intake Converter · 2.02\n','Click ▶ once, then drop one or multiple **XLSX/CSV files** into the upload area or choose files. Conversion starts automatically.\n','Outputs: v3.1 and EC_upload. Any row with extra constructs rejects normal conversion for the entire workbook; a separate DNA-only construct table and assembly audit are produced when DNA checks pass.\n']},
        {'cell_type':'code','metadata':{'id':'converter','cellView':'form','tags':['hide-input']},'source':code.splitlines(True),'outputs':[],'execution_count':None}]}
    path=ROOT/'Twist_Unified_Intake_Converter_v2.02.ipynb'
    path.write_text(json.dumps(notebook,indent=1));return path

if __name__=='__main__':print(build())
