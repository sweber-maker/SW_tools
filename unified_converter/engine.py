"""Load the uploaded notebook's engines unchanged, without running Colab uploads/installers."""
import ast
import json
from pathlib import Path

NOTEBOOK = Path(__file__).with_name('Twist_Unified_Intake_Converter_v2.0.ipynb')

def load_engine():
    notebook=json.loads(NOTEBOOK.read_text())
    namespace={'__name__':'unified_converter_under_test'}
    for index in (2,3,4):
        exec(compile(''.join(notebook['cells'][index]['source']),str(NOTEBOOK)+f':cell{index}','exec'),namespace)
    # Only imports and function definitions from the routing cell: never execute upload/download.
    tree=ast.parse(''.join(notebook['cells'][5]['source']))
    tree.body=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef))
               and not (isinstance(node,ast.ImportFrom) and node.module=='google.colab')]
    exec(compile(tree,str(NOTEBOOK)+':routing','exec'),namespace)
    return namespace
