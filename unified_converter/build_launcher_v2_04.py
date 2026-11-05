"""Keep browser notebooks tiny; put unchanged converter sources in a verified runtime ZIP."""
import ast
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
VERSION='2.04'
URL=f'https://raw.githubusercontent.com/sweber-maker/SW_tools/unified-v{VERSION}/unified_converter/releases/unified_v{VERSION}.zip'

BOOTSTRAP='''# @title ▶ Start converter { display-mode: "form" }
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from IPython.display import clear_output

VERSION = "__VERSION__"
BUNDLE_URL = "__URL__"
BUNDLE_SHA256 = "__SHA256__"
BUNDLE_BYTES = __BYTES__
print("Starting converter " + VERSION + "…")
try:
    with urllib.request.urlopen(BUNDLE_URL, timeout=30) as response:
        payload = response.read(BUNDLE_BYTES + 1)
    if hashlib.sha256(payload).hexdigest() != BUNDLE_SHA256:
        raise ValueError("Converter download did not match this release. Please reopen START_HERE.")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet",
         "openpyxl==3.1.5", "lxml>=5,<7"],
        check=True, capture_output=True, text=True,
    )
    work_dir = Path(tempfile.mkdtemp(prefix="sw-tools-" + VERSION + "-"))
    with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
        for entry in bundle.infolist():
            path = Path(entry.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Invalid converter package path.")
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Invalid converter package link.")
        bundle.extractall(work_dir)
    namespace = {"__name__": "sw_tools_launcher",
                 "__file__": str(work_dir / "launch.py")}
    exec(compile((work_dir / "launch.py").read_text(), "launch.py", "exec"), namespace)
    clear_output(wait=True)
    _engine, _controls = namespace["start"](work_dir)
except Exception as exc:
    print("Could not start the converter: " + str(exc))
    print("Please reopen START_HERE and run this cell again.")
    raise
'''

LAUNCH='''"""Load this release's sources on the Python runtime, outside the browser editor."""
import json
from pathlib import Path

def initialize(directory):
    directory=Path(directory)
    sources=json.loads((directory/'sources.json').read_text())
    runtime={'__name__':'sw_tools_runtime'}
    exec(compile((directory/'runtime.py').read_text(),'runtime.py','exec'),runtime)
    return runtime['initialize'](sources,directory/'engine')

def start(directory):
    directory=Path(directory)
    engine=initialize(directory)
    ui={'__name__':'sw_tools_ui','__file__':str(directory/'colab_ui.py')}
    exec(compile((directory/'colab_ui.py').read_text(),'colab_ui.py','exec'),ui)
    controls=ui['show_converter'](engine['run_unified'])
    return engine,controls
'''


def build():
    previous=json.loads((ROOT/'Twist_Unified_Intake_Converter_v2.03.ipynb').read_text())
    tree=ast.parse(''.join(previous['cells'][1]['source']))
    literals={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body
              if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
              and node.targets[0].id in ('RELEASE_SOURCES','RUNTIME_SOURCE')}
    sources=literals['RELEASE_SOURCES']
    # Only version identifiers change. All scientific mappings/assembly code stays frozen.
    assert "VERSION = '2.03'" in sources['v3_engine']
    assert 'VERSION = "2.03"' in sources['routing']
    sources['v3_engine']=sources['v3_engine'].replace("VERSION = '2.03'","VERSION = '2.04'",1)
    sources['routing']=sources['routing'].replace('VERSION = "2.03"','VERSION = "2.04"',1)
    files={'sources.json':json.dumps(sources,ensure_ascii=True).encode(),
           'runtime.py':literals['RUNTIME_SOURCE'].encode(),
           'launch.py':LAUNCH.encode(),
           'colab_ui.py':(ROOT/'ui_v2_03/colab_ui.py').read_bytes(),
           'upload.html':(ROOT/'ui_v2_03/upload.html').read_text().replace('2.03','2.04').encode()}
    manifest={'version':VERSION,'files':{name:hashlib.sha256(blob).hexdigest() for name,blob in files.items()}}
    files['manifest.json']=json.dumps(manifest,indent=2).encode()
    memory=io.BytesIO()
    with zipfile.ZipFile(memory,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,blob in files.items():
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            archive.writestr(info,blob)
    package=memory.getvalue();digest=hashlib.sha256(package).hexdigest()
    release=ROOT/'releases'/f'unified_v{VERSION}.zip';release.parent.mkdir(exist_ok=True);release.write_bytes(package)
    code=BOOTSTRAP.replace('__VERSION__',VERSION).replace('__URL__',URL).replace('__SHA256__',digest).replace('__BYTES__',str(len(package)))
    compile(code,'launcher','exec')
    descriptor={'version':VERSION,'bundle_filename':release.name,'bundle_sha256':digest,'bundle_url':URL}
    notebook={'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'colab':{'name':'Twist Converter '+VERSION,'provenance':[]},'sw_tools':descriptor},
        'cells':[
            {'id':'intro','cell_type':'markdown','metadata':{'id':'intro'},'source':[
                '# Antibody form converter · '+VERSION+'\n',
                '**Click ▶ below once**, then choose or drop one or multiple XLSX/CSV files.\n',
                'The converter loads from GitHub when you start it. Download names retain your source filename and version.\n'],},
            {'id':'converter','cell_type':'code','metadata':{'id':'converter','cellView':'form','tags':['hide-input']},
             'source':code.splitlines(True),'outputs':[],'execution_count':None}]}
    encoded=json.dumps(notebook,indent=1)+'\n'
    archived=ROOT/f'Twist_Unified_Intake_Converter_v{VERSION}.ipynb';archived.write_text(encoded)
    (ROOT.parent/'START_HERE.ipynb').write_text(encoded)
    (ROOT/'releases'/f'unified_v{VERSION}_manifest.json').write_text(json.dumps({**descriptor,'bundle_bytes':len(package),'notebook_bytes':len(encoded.encode()),'notebook_sha256':hashlib.sha256(encoded.encode()).hexdigest()},indent=2)+'\n')
    return release,archived

if __name__=='__main__':
    for path in build():print(path)
