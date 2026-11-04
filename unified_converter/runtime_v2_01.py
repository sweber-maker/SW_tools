"""Initialize isolated unified and v3.1 engines from notebook-embedded source assets."""
import base64
from pathlib import Path


def initialize(sources, directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    template_dir=directory/'templates';template_dir.mkdir(exist_ok=True)
    (template_dir/'v3.1.xlsx').write_bytes(base64.b64decode(sources['v3_template']))
    namespace={'__name__':'unified_release','__file__':str(directory/'unified.py')}
    exec(compile(sources['assets'],'embedded_templates','exec'),namespace)
    exec(compile(sources['ec_engine'],'embedded_ec_engine','exec'),namespace)
    # Keep norm/MAP/options and other v3 globals out of the EC engine namespace.
    v3={'__name__':'unified_v3','__file__':str(directory/'v3_engine.py')}
    exec(compile(sources['v3_engine'],'embedded_v3_engine','exec'),v3)
    namespace['convert_v3']=v3['convert']
    exec(compile(sources['routing'],'embedded_routing','exec'),namespace)
    return namespace
