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
    extra={'__name__':'unified_constructs'}
    exec(compile(sources['constructs'],'embedded_constructs','exec'),extra)
    namespace.update({key:extra[key] for key in ('inspect_v42','fallback_table','ExtraConstructError')})
    def guarded(fn):
        def call(blob,*args,**kwargs):
            if isinstance(blob,(bytes,bytearray)) and bytes(blob).startswith(b'PK'):
                extra['reject_extra'](blob)
            return fn(blob,*args,**kwargs)
        return call
    for key in ('convert_v3','convert_bytes','convert_routed','process_one'):
        namespace[key]=guarded(namespace[key])
    original=namespace['convert_to_v42']
    def to_v42(rows,*args,**kwargs):
        if any(len(record['chains'])>2 for record in rows):
            raise extra['ExtraConstructError']('Normal conversion rejected: more than two normalized construct chains')
        return original(rows,*args,**kwargs)
    namespace['convert_to_v42']=to_v42
    return namespace
