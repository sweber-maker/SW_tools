"""Antigen lookup 1.01: shared conservative lookup engine."""
import re
from urllib.parse import urlparse, quote
import requests
from bs4 import BeautifulSoup
from Bio.SeqUtils.ProtParam import ProteinAnalysis
VERSION = "1.01"
HEAD={'User-Agent':'Mozilla/5.0 (compatible; AntigenLookup/1.01)'}
FIELDS=['Target Antigen Name','Target Antigen Tags','Target Antigen Supplier','Supplied Target Antigen Storage Conditions','Supplied Target Antigen Details (Formulation/Storage Buffer)','Vendor-Supplied Target Antigen (URL and Catalog #)','Target Antigen Requests','Molecular Weight (kDa)','Extinction Coefficient (M-1cm-1)','Oligomeric Condition','Affinity','Homology']

def get(url):
    try:
        r=requests.get(url,headers=HEAD,timeout=18);r.raise_for_status();return r
    except requests.RequestException:return None

def uniprot(acc):
    r=get(f'https://rest.uniprot.org/uniprotkb/{quote(acc)}.json')
    if not r:return None
    try:return r.json()
    except ValueError:return None

def classify(x):
    x=x.strip()
    if re.match(r'^https?://',x,re.I):return 'url'
    if re.fullmatch(r'(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(?:-\d+)?',x,re.I):return 'uniprot'
    if re.fullmatch(r'\d{4,7}-[A-Za-z0-9-]+',x):return 'catalog'
    return 'name'

def lookup(raw, vendor='Auto', exact_sequence='', source_sequence='', page_cache=None):
    raw=str(raw).strip();kind=classify(raw)
    values={k:'' for k in FIELDS}; evidence=[]; alerts=[]
    def put(k,v,confidence,source,note=''):
        values[k]=v;evidence.append({'Field':k,'Value':v,'Confidence':confidence,'Source':source,'Notes':note})
    if vendor!='Auto':put('Target Antigen Supplier',vendor,'User-provided','User input')
    if kind=='catalog':
        if vendor in ('Auto','Sino Biological'):
            put('Target Antigen Supplier','Sino Biological','Inferred','Catalog format; confirm product match')
            alerts.append('Catalog format resembles Sino Biological. Exact product page has not been verified. Paste the manufacturer URL for source extraction.')
        else:alerts.append('Catalog supplied without a verified product URL. Product-specific properties withheld.')
        put('Vendor-Supplied Target Antigen (URL and Catalog #)',raw,'User-provided','User input')
    if kind=='name':put('Target Antigen Name',raw,'User-provided','User input')
    if kind=='uniprot':
        data=uniprot(raw)
        if data:
            nm=data.get('proteinDescription',{}).get('recommendedName',{}).get('fullName',{}).get('value','')
            put('Target Antigen Name',nm or raw,'Reference only','UniProt '+raw,'Canonical protein identity; not necessarily vendor construct')
            alerts.append('UniProt describes a reference sequence, not the exact commercial construct. Vendor-specific values withheld.')
        else:alerts.append('UniProt record unavailable; check accession and internet access.')
    if kind=='url':
        host=urlparse(raw).netloc.lower()
        known={'sinobiological.com':'Sino Biological','acrobiosystems.com':'ACROBiosystems','genscript.com':'GenScript'}
        supplier=next((v for k,v in known.items() if host==k or host.endswith('.'+k)),None)
        if supplier:put('Target Antigen Supplier',supplier,'Verified domain',raw)
        else:alerts.append('URL is not from a recognized supplier; confirm source manually.')
        put('Vendor-Supplied Target Antigen (URL and Catalog #)',raw,'User-provided','User input')
        response=get(raw)
        if response:
            soup=BeautifulSoup(response.text,'html.parser')
            for t in soup(['script','style','nav','footer']):t.decompose()
            title=soup.title.get_text(' ',strip=True) if soup.title else ''
            if title:put('Target Antigen Name',title[:180],'Product page title',raw,'Page title only; confirm actual protein identity')
            page=soup.get_text(' ',strip=True)
            if page_cache is not None: page_cache[raw]=page[:40000]
            alerts.append('Product page retrieved. Manufacturer text is available for manual review; no MW, buffer, affinity, or oligomeric state is inferred from unstructured text.')
        else:alerts.append('Could not retrieve product page; it may block automated requests.')
    if exact_sequence.strip():
        seq=re.sub(r'\s+','',exact_sequence).upper()
        if re.fullmatch('[ACDEFGHIKLMNPQRSTVWY]+',seq):
            if not source_sequence.strip():
                alerts.append('Sequence provided but no verification source. Extinction coefficient not automatically accepted.')
            else:
                p=ProteinAnalysis(seq)
                er,eo=p.molar_extinction_coefficient()
                put('Extinction Coefficient (M-1cm-1)',str(er) if er==eo else '', 'Calculated / conditional',source_sequence.strip(),f'Exact sequence claimed verified. Reduced ε={er:,}; maximum oxidized ε={eo:,} M⁻¹cm⁻¹. Blank when disulfide state changes value.')
                if er!=eo:alerts.append(f'Extinction coefficient depends on disulfides: reduced {er:,}; maximum oxidized {eo:,}. No single high-confidence value selected.')
                else:alerts.append(f'Calculated ε280={er:,} M⁻¹cm⁻¹; confirm the supplied sequence is the full mature construct.')
        else:alerts.append('Invalid sequence characters; extinction coefficient withheld.')
    if not evidence:alerts.append('No verified manufacturer data found. Provide a direct product URL or verified construct sequence.')
    return values,evidence,alerts
