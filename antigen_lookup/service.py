"""Shared report service for Streamlit and Colab, version 1.01."""
import io
import re
from pathlib import Path
from urllib.parse import urlparse, urljoin
import pandas as pd
import requests
from core import FIELDS, VERSION
from extract import extract, manufacturer, pack_options
from quantity import calculate


def fetch(url):
    for _ in range(6):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or not manufacturer(url) or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError('Use an HTTPS ACROBiosystems, Sino Biological, or GenScript product URL.')
        r = requests.get(url, timeout=25, allow_redirects=False,
                         headers={'User-Agent': 'AntigenLookup/1.01 (research tool)'})
        if r.is_redirect:
            url = urljoin(url, r.headers['Location'])
            continue
        r.raise_for_status()
        if 'html' not in r.headers.get('Content-Type', '').lower():
            raise ValueError('Expected an HTML product page; PDF extraction is not supported yet.')
        return r.text, url
    raise ValueError('Too many redirects.')


def report(url, catalog='', format='BLI', antibodies=96, mw_kda=None, oligomer=None, mw_basis='monomer', html=None):
    warnings = []
    source = url
    try:
        if html is None: html, source = fetch(url)
        evidence, offers, text, warnings = extract(html, source, catalog)
    except (requests.RequestException, ValueError) as e:
        evidence, offers, text = [], [], ''
        warnings = [f'Product retrieval failed: {e}. No vendor properties or availability verified.']
    values = {field: '' for field in FIELDS}
    values['Target Antigen Supplier'] = 'Vendor-Supplied'
    values['Vendor-Supplied Target Antigen (URL and Catalog #)'] = f'{source} {catalog}'.strip()
    for field in values:
        choices = list(dict.fromkeys(r['Value'] for r in evidence if r['Field'] == field))
        if len(choices) == 1: values[field] = choices[0]
        elif len(choices) > 1: warnings.append(f'Conflicting {field} values; left blank for review.')
    calculation = None
    if mw_kda and oligomer:
        calculation = calculate(format, antibodies, mw_kda, oligomer, mw_basis)
        values['Target Antigen Requests'] = f"{calculation['Purchase target (ug)']} ug"
        evidence.append({'Field': 'Quantity calculation inputs', 'Value': f'{mw_kda} kDa; oligomer {oligomer}; MW basis {mw_basis}', 'Source': 'User-confirmed inputs', 'Status': 'User-provided; verify against exact construct'})
    else:
        warnings.append('Confirm molecular weight, its monomer/assembly basis, and oligomeric condition before calculating quantity. Unknown is not assumed monomer.')
    options = pack_options(offers, calculation['Purchase target (ug)']) if calculation else []
    return {'Intake': [{'Field': k, 'Value': v} for k,v in values.items()], 'Evidence': evidence,
            'Offers': offers, 'Purchase options': options, 'Calculation': [calculation] if calculation else [],
            'Review flags': [{'Warning': w} for w in warnings],
            'Manufacturer text': [{'Text': text}], 'Metadata': [{'Version': VERSION, 'Manufacturer': manufacturer(source), 'Catalog': catalog,
                'Calculator': 'SPR (Carterra) & BLI (Octet) & ELISA_Reagent Amt_Reference.xlsx; H15 / H40; already two runs'}]}


def excel(result):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter', engine_kwargs={'options': {'strings_to_formulas': False, 'strings_to_urls': False}}) as writer:
        for sheet, rows in result.items(): pd.DataFrame(rows).to_excel(writer, sheet_name=sheet[:31], index=False)
    return buffer.getvalue()


def batch(name, data, **settings):
    frame = pd.read_csv(io.BytesIO(data)) if name.lower().endswith('.csv') else pd.read_excel(io.BytesIO(data))
    if 'URL' not in frame.columns: raise ValueError('Batch files need a URL column; optional columns: Catalog, MW_kDa, Oligomer, MW_basis, Format, Antibodies.')
    combined = {}
    for index, row in frame.fillna('').iterrows():
        opts = dict(settings)
        for col, key in [('Catalog','catalog'),('MW_kDa','mw_kda'),('Oligomer','oligomer'),('MW_basis','mw_basis'),('Format','format'),('Antibodies','antibodies')]:
            if col in row and row[col] != '': opts[key] = row[col]
        try:
            for key in ('mw_kda',):
                if opts.get(key): opts[key] = float(opts[key])
            for key in ('oligomer','antibodies'):
                if opts.get(key):
                    value = float(opts[key])
                    if not value.is_integer(): raise ValueError(f'{key} must be a whole number')
                    opts[key] = int(value)
            result = report(str(row['URL']), **opts)
        except (ValueError, TypeError) as e:
            result = {'Review flags': [{'Warning': str(e)}]}
        for sheet, rows in result.items():
            combined.setdefault(sheet, []).extend({'Input row': index+2, 'Input URL': row['URL'], **r} for r in rows)
    if frame.empty: raise ValueError('No input rows found.')
    return excel(combined)


def output_name(name):
    return f'{Path(name).stem}_lookup_v{VERSION}.xlsx'
