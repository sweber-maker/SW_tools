"""Reject extra constructs in normal routes and prepare auditable DNA-only fallback tables."""
import io
import re
from collections import Counter
import openpyxl

BLOCKS=((8,14),(15,21),(23,29),(30,36))  # zero-based name and insert-sequence columns

class ExtraConstructError(ValueError):
    pass


def meaningful(value):
    return value is not None and str(value).strip()!='' and 'PLEASE SELECT' not in str(value).upper()


def inspect_v42(blob):
    workbook=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=False)
    cached=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
    try:
        if 'Antibody Designs' not in workbook.sheetnames:return {'extra_rows':[],'rows':[]}
        rows=[];extra=[]
        raw_rows=workbook['Antibody Designs'].iter_rows(min_row=4,max_col=37,values_only=True)
        cached_rows=cached['Antibody Designs'].iter_rows(min_row=4,max_col=37,values_only=True)
        for number,(raw,calculated) in enumerate(zip(raw_rows,cached_rows),4):
            values=list(raw)
            for column,value in enumerate(values):
                if isinstance(value,str) and value.startswith('='):
                    if meaningful(calculated[column]):values[column]=calculated[column]
                    elif column==29 and value==f'=IF(Y{number} =\'Dropdown Lists\'!$B$115,\'Dropdown Lists\'!$E$104,"")' and not meaningful(raw[24]):
                        # Known blank AD formula scaffold from the bundled v4.2 template.
                        # Unknown/unresolved formulas remain evidence, never assumed blank.
                        values[column]=None
            blocks=[]
            for index,(start,end) in enumerate(BLOCKS,1):
                block=values[start:end+1]
                if any(meaningful(v) for v in block):
                    blocks.append({'index':index,'name':values[start],'vector':values[start+1],
                                   'kozak':values[start+3],'leader':values[start+5],'sequence':values[end],
                                   'kozak_setting':values[start+2],'leader_setting':values[start+4]})
            ratio=values[22]
            # W is specifically the 3–4 construct ratio field in v4.2.
            ratio_parts=str(ratio).split(':') if meaningful(ratio) else []
            is_extra=any(b['index']>=3 for b in blocks) or (meaningful(ratio) and len(ratio_parts)!=2)
            if blocks or meaningful(values[2]) or is_extra:
                record={'row':number,'antibody':values[2],'constructs':blocks,'ratio':ratio}
                rows.append(record)
                if is_extra:extra.append(number)
        return {'extra_rows':extra,'rows':rows}
    finally:workbook.close();cached.close()


def reject_extra(blob):
    inspection=inspect_v42(blob)
    if inspection['extra_rows']:
        raise ExtraConstructError('Normal conversion rejected: unsupported 3–4 construct fields on source rows '+', '.join(map(str,inspection['extra_rows'])))
    return inspection


def dna(value,field,required=False):
    if not meaningful(value):
        if required:raise ValueError(f'{field}: DNA sequence is missing')
        return ''
    result=re.sub(r'\s+','',str(value)).upper()
    if not re.fullmatch('[ACGT]+',result):
        raise ValueError(f'{field}: expected literal DNA using A/C/G/T only; protein, ambiguous bases, formulas and menu text cannot be converted to verified DNA')
    return result


def assemble_dna(kozak,leader,sequence):
    """Never reverse translate, trim overlaps, or alter uncertain internal signal matches."""
    k=dna(kozak,'Kozak');l=dna(leader,'Leader');s=dna(sequence,'Insert',required=True)
    warnings=[]
    if not k:warnings.append('Kozak not supplied separately; its presence cannot be verified')
    if not l:warnings.append('Leader not supplied separately; its presence cannot be verified')
    prefix=k+l
    if k and l.startswith(k):
        prefix=l;warnings.append('Leader field already includes the complete Kozak; no duplicate added')
    if not prefix:return s,'input retained; no separate prefix supplied',warnings
    offset=s.find(prefix)
    if offset>=0:
        if offset>0 and k and not l:
            raise ValueError('Only the separately supplied component occurs internally; manual DNA review required')
        if s.count(prefix)>1:warnings.append('Input already contains multiple copies of the supplied prefix; retained unchanged for review')
        return s,f'complete prefix already present at offset {offset}; input retained',warnings
    if k and l and s.startswith(l):
        if s[len(l):].startswith(k):
            raise ValueError('Kozak/leader occurs internally or out of order; manual DNA review required')
        if k in s:warnings.append('Kozak motif also occurs internally; only the missing 5-prime Kozak was added')
        return k+s,'leader already present; Kozak prepended',warnings
    if k and l and s.startswith(k) and l not in s:
        return prefix+s[len(k):],'Kozak already present; leader inserted immediately after it',warnings
    # An individual signal occurring internally or in the wrong order is not enough
    # evidence to edit a coding sequence. Return a review failure instead of guessing.
    if (k and k in s) or (l and l in s):
        raise ValueError('Kozak/leader occurs internally or out of order; manual DNA review required to avoid duplication or coding-sequence edits')
    # Do not infer how to merge a partially included signal. Short coincidental
    # base matches are never trimmed; these thresholds only flag review cases.
    for label,component,minimum in (('Kozak',k,6),('Leader',l,12)):
        if any(s.startswith(component[:n]) or s.startswith(component[-n:]) for n in range(minimum,len(component))):
            raise ValueError(f'Possible partial {label} at insert start; manual DNA review required')
    return prefix+s,'Kozak and leader prepended in order',warnings


def fallback_table(inspection):
    rows=[];audit=[];errors=[]
    for record in inspection['rows']:
        if not record['constructs']:
            errors.append(f"Row {record['row']}: named design has no construct sequence fields")
        for block in record['constructs']:
            name=str(block['name']).strip() if meaningful(block['name']) else f"{record['antibody'] or 'row_'+str(record['row'])}_construct_{block['index']}"
            entry={'source_row':record['row'],'construct':block['index'],'name':name,'antibody':record['antibody'],'warnings':[]}
            try:
                sequence,action,warnings=assemble_dna(block['kozak'],block['leader'],block['sequence'])
                entry.update(action=action,dna_length=len(sequence),warnings=warnings)
                if not meaningful(block['name']):entry['warnings'].append('Construct name derived from antibody name and construct index')
                if not meaningful(block['vector']):entry['warnings'].append('Vector name not supplied; left blank')
                rows.append((name,sequence,str(block['vector']).strip() if meaningful(block['vector']) else ''))
            except ValueError as exc:
                entry['error']=str(exc);errors.append(f"Row {record['row']}, construct {block['index']} ({name}): {exc}")
            audit.append(entry)
        if meaningful(record['ratio']):
            parts=str(record['ratio']).split(':')
            if len(parts) in (3,4) and len(record['constructs'])!=len(parts):
                errors.append(f"Row {record['row']}: transfection ratio declares {len(parts)} constructs but {len(record['constructs'])} construct blocks are populated")
    duplicates=[name for name,count in Counter(row[0] for row in rows).items() if count>1]
    for entry in audit:
        if entry['name'] in duplicates:
            entry['warnings'].append('Construct name appears on multiple source rows; retained without deduplication; review name/sequence identity')
    if not rows:errors.append('No DNA constructs available for fallback export')
    if errors:return None,audit,errors
    workbook=openpyxl.Workbook();sheet=workbook.active;sheet.title='DNA Constructs'
    sheet.append(['Name','Sequence','Vector Name'])
    for row in rows:
        sheet.append(row)
        for cell in sheet[sheet.max_row]:cell.data_type='s'  # names/vectors remain literal text, never formulas
    sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
    for column,width in [('A',36),('B',90),('C',50)]:sheet.column_dimensions[column].width=width
    output=io.BytesIO();workbook.save(output);workbook.close()
    return output.getvalue(),audit,[]
