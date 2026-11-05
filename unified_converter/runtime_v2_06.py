"""Initialize isolated unified and v3.1 engines from notebook-embedded source assets."""
import base64
import csv
import io
import json
import re
import zipfile
from pathlib import Path


def initialize(sources, directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    template_dir=directory/'templates';template_dir.mkdir(exist_ok=True)
    (template_dir/'v3.1.xlsx').write_bytes(base64.b64decode(sources['v3_template']))
    intake={'__name__':'unified_intake'}
    exec(compile(sources['intake'],'embedded_intake','exec'),intake)
    namespace={'__name__':'unified_release','__file__':str(directory/'unified.py')}
    exec(compile(sources['assets'],'embedded_templates','exec'),namespace)
    signals={'__name__':'unified_signals'}
    exec(compile(sources['signals'],'embedded_signals','exec'),signals)
    namespace.update(signal_dna=signals['dna'],signal_resolve=signals['resolve'])
    exec(compile(sources['ec_engine'],'embedded_ec_engine','exec'),namespace)
    # Keep norm/MAP/options and other v3 globals out of the EC engine namespace.
    v3={'__name__':'unified_v3','__file__':str(directory/'v3_engine.py')}
    exec(compile(sources['v3_engine'],'embedded_v3_engine','exec'),v3)
    def corrected_v3(blob):
        prepared,audit=signals['prepare'](blob)
        content,count,issues=v3['convert'](prepared)
        for item in audit:issues.append({**item,'version':v3['VERSION']})
        return content,count,issues
    namespace['convert_v3']=corrected_v3
    original_ec=namespace['convert_bytes']
    def corrected_ec(blob,name,templates):
        prepared,audit=signals['prepare'](blob)
        content,notes,meta=original_ec(prepared,name,templates)
        messages=[f"{item['location']} {item['field']}: {item['status']}" for item in audit]
        meta['warnings'].extend(messages)
        meta['signal_corrections']=audit
        if messages:notes+='\nSignal field corrections/review:\n'+'\n'.join(messages)
        return content,notes,meta
    namespace['convert_bytes']=corrected_ec
    namespace.update(intake_identify=intake['identify'],intake_validate=intake['validate_normal_rows'])
    exec(compile(sources['routing'],'embedded_routing','exec'),namespace)
    extra={'__name__':'unified_constructs'}
    exec(compile(sources['constructs'],'embedded_constructs','exec'),extra)
    namespace.update({key:extra[key] for key in ('inspect_v42','fallback_table','ExtraConstructError')})
    def guarded(fn):
        def call(blob,*args,**kwargs):
            blob,_=intake['normalize'](blob)
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
    original_run=namespace['run_unified']
    def run(uploaded,output_dir='converted'):
        archives=[]
        for name,blob in uploaded.items():
            try:prepared,is_intake=intake['normalize'](blob)
            except Exception:prepared=blob;is_intake=False  # Delegate to the standard per-file failure report.
            produced=original_run({name:prepared},output_dir)
            if is_intake:
                for path in produced:
                    with zipfile.ZipFile(path) as package:
                        entries=[(item,package.read(item.filename)) for item in package.infolist()]
                    rewritten=[]
                    for item,data in entries:
                        if item.filename.endswith('_DNA_constructs_audit.json'):
                            audit=json.loads(data);audit['source_sheet']='Sequence'
                            audit['extra_construct_rows']=[row-2 for row in audit['extra_construct_rows']]
                            for record in audit['constructs']:record['source_row']-=2
                            data=json.dumps(audit,indent=2,default=str).encode()
                        elif item.filename.endswith('_report.csv'):
                            rows=list(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
                            for row in rows[1:]:
                                if len(row)>4 and 'construct fields found on source rows ' in row[4]:
                                    prefix,positions=row[4].split('source rows ',1)
                                    row[4]=prefix+'source rows '+', '.join(str(int(number.strip())-2) for number in positions.split(','))
                            buffer=io.StringIO();writer=csv.writer(buffer);writer.writerows(rows);data=buffer.getvalue().encode('utf-8-sig')
                        rewritten.append((item,data))
                    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as package:
                        for item,data in rewritten:package.writestr(item,data)
            archives.extend(produced)
        return archives
    namespace['run_unified']=run
    return namespace
