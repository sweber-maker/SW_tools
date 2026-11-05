"""Load archived notebook engines or a verified release package for local regression tests."""
import ast
import json
import hashlib
import io
import zipfile
import tempfile
from pathlib import Path

NOTEBOOK = Path(__file__).with_name('Twist_Unified_Intake_Converter_v2.0.ipynb')

def load_engine(path=NOTEBOOK):
    path=Path(path)
    notebook=json.loads(path.read_text())
    descriptor=notebook.get('metadata',{}).get('sw_tools')
    if descriptor:
        name=descriptor['bundle_filename']
        if Path(name).name!=name:raise ValueError('Invalid package filename')
        payload=(Path(__file__).parent/'releases'/name).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=descriptor['bundle_sha256']:
            raise ValueError('Runtime package checksum mismatch')
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            sources=json.loads(archive.read('sources.json'))
            runtime_source=archive.read('runtime.py').decode()
        runtime={'__name__':'unified_runtime'}
        exec(compile(runtime_source,'runtime.py','exec'),runtime)
        workspace=tempfile.TemporaryDirectory(prefix='unified-launcher-test-')
        namespace=runtime['initialize'](sources,workspace.name)
        namespace['_workspace']=workspace
        if namespace['VERSION']!=descriptor['version']:raise ValueError('Runtime version mismatch')
        return namespace
    if len(notebook['cells'])==2:
        tree=ast.parse(''.join(notebook['cells'][1]['source']))
        literals={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
                  and node.targets[0].id in ('RELEASE_SOURCES','RUNTIME_SOURCE')}
        runtime={'__name__':'unified_runtime'}
        exec(compile(literals['RUNTIME_SOURCE'],'runtime','exec'),runtime)
        workspace=tempfile.TemporaryDirectory(prefix='unified-test-')
        namespace=runtime['initialize'](literals['RELEASE_SOURCES'],workspace.name)
        namespace['_workspace']=workspace
        return namespace
    namespace={'__name__':'unified_converter_under_test'}
    for index in (2,3,4):
        exec(compile(''.join(notebook['cells'][index]['source']),str(NOTEBOOK)+f':cell{index}','exec'),namespace)
    # Only imports and function definitions from the routing cell: never execute upload/download.
    tree=ast.parse(''.join(notebook['cells'][5]['source']))
    tree.body=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef))
               and not (isinstance(node,ast.ImportFrom) and node.module=='google.colab')]
    exec(compile(tree,str(NOTEBOOK)+':routing','exec'),namespace)
    return namespace
