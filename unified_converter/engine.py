"""Load the uploaded notebook's engines unchanged, without running Colab uploads/installers."""
import ast
import json
import tempfile
from pathlib import Path

NOTEBOOK = Path(__file__).with_name('Twist_Unified_Intake_Converter_v2.0.ipynb')

def load_engine(path=NOTEBOOK):
    path=Path(path)
    notebook=json.loads(path.read_text())
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
