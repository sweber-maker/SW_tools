"""Conservative source extraction. Candidates require product-specific review."""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from bs4 import BeautifulSoup

DOMAINS = {'acrobiosystems.com': 'ACROBiosystems', 'sinobiological.com': 'Sino Biological', 'genscript.com': 'GenScript'}
LABELS = {
    'Target Antigen Tags': ('Tag', 'Tags', 'Protein Tag'),
    'Supplied Target Antigen Storage Conditions': ('Storage', 'Storage Conditions', 'Stability & Storage'),
    'Supplied Target Antigen Details (Formulation/Storage Buffer)': ('Formulation', 'Buffer', 'Storage Buffer', 'Formulation/Storage'),
    'Molecular Weight (kDa)': ('Molecular Weight', 'Predicted Molecular Weight', 'Calculated Molecular Weight'),
    'Oligomeric Condition': ('Oligomeric State', 'Oligomeric Condition', 'Oligomerization'),
    'Extinction Coefficient (M-1cm-1)': ('Extinction Coefficient', 'Extinction Coefficient (M-1cm-1)'),
    'Affinity': ('Affinity', 'Binding Affinity'),
    'Homology': ('Homology', 'Sequence Homology', 'Sequence Identity'),
}


def manufacturer(url):
    host = (urlparse(url).hostname or '').lower()
    return next((v for k, v in DOMAINS.items() if host == k or host.endswith('.' + k)), '')


def extract(html, url, catalog=''):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    offers = []
    timestamp = datetime.now(timezone.utc).isoformat()
    def add(field, value, excerpt, status='Extracted candidate; review required'):
        records.append({'Field': field, 'Value': str(value), 'Source': url,
                        'Excerpt': str(excerpt)[:1500], 'Status': status, 'Retrieved UTC': timestamp})
    products = []
    def visit(node):
        if isinstance(node, list):
            for item in node: visit(item)
        elif isinstance(node, dict):
            types = node.get('@type', [])
            if isinstance(types, str): types = [types]
            if 'Product' in types: products.append(node)
            if '@graph' in node: visit(node['@graph'])
    for script in soup.find_all('script', type='application/ld+json'):
        try: visit(json.loads(script.string or script.get_text()))
        except (ValueError, TypeError): pass
    # Never combine unrelated recommendation products. Catalog matching is mandatory
    # when the user supplies one; a page title mention alone does not verify a SKU.
    selected = [p for p in products if catalog and str(p.get('sku', p.get('mpn', ''))).casefold() == catalog.casefold()]
    if not catalog and len(products) == 1: selected = products
    for p in selected:
        if p.get('name'): add('Target Antigen Name', p['name'], json.dumps(p, ensure_ascii=False))
        if p.get('sku'): add('Catalog #', p['sku'], p['sku'])
        raw_offers = p.get('offers', [])
        if isinstance(raw_offers, dict): raw_offers = [raw_offers]
        for offer in raw_offers:
            # AggregateOffer prices cannot be attributed to a pack size.
            if not isinstance(offer, dict): continue
            offers.append({'Pack / variant': offer.get('name', ''), 'Price': offer.get('price', ''),
                           'Currency': offer.get('priceCurrency', ''),
                           'Availability': str(offer.get('availability', '')).rsplit('/', 1)[-1],
                           'Source': url, 'Retrieved UTC': timestamp,
                           'Status': 'Review pack size, region and current checkout price'})
    for t in soup(['script', 'style', 'nav', 'footer']): t.decompose()
    text = soup.get_text(' ', strip=True)
    if catalog and not re.search(r'(?<![A-Za-z0-9])'+re.escape(catalog)+r'(?![A-Za-z0-9])', text, re.I):
        return [], [], text, ['Catalog number not found on page; product fields withheld.']
    title = soup.find('h1')
    if title and not any(r['Field'] == 'Target Antigen Name' for r in records):
        add('Target Antigen Name', title.get_text(' ', strip=True), str(title))
    pairs = []
    for tr in soup.find_all('tr'):
        cells = tr.find_all(['th', 'td'], recursive=False)
        if len(cells) == 2: pairs.append(tuple(c.get_text(' ', strip=True) for c in cells))
    for dt in soup.find_all('dt'):
        dd = dt.find_next_sibling('dd')
        if dd: pairs.append((dt.get_text(' ', strip=True), dd.get_text(' ', strip=True)))
    for label, value in pairs:
        normalized = label.strip().rstrip(':').casefold()
        for field, names in LABELS.items():
            if normalized in [n.casefold() for n in names] and value:
                add(field, value, label + ': ' + value)
    if manufacturer(url): add('Manufacturer', manufacturer(url), url, 'Recognized manufacturer domain')
    warnings = ['Extracted values are candidates, not verified scientific results. Review the exact construct and sources.']
    if not offers: warnings.append('No product-linked structured price/stock found. Check vendor page or request a quote; availability is unknown.')
    return records, offers, text[:40000], warnings


def pack_options(offers, target_ug):
    """Only price explicitly named single-size offers; never infer from global text."""
    from decimal import Decimal, InvalidOperation, ROUND_CEILING
    results = []
    for offer in offers:
        name = str(offer.get('Pack / variant', ''))
        sizes = re.findall(r'(\d+(?:\.\d+)?)\s*(µg|μg|ug|mg)\b', name, re.I)
        if len(sizes) != 1: continue
        amount, unit = sizes[0]
        size = Decimal(amount) * (1000 if unit.lower() == 'mg' else 1)
        try:
            price = Decimal(str(offer.get('Price', '')))
            if size <= 0 or not price.is_finite() or price < 0: continue
        except InvalidOperation: continue
        if not offer.get('Currency'): continue
        count = int((Decimal(str(target_ug)) / size).to_integral_value(rounding=ROUND_CEILING))
        results.append({**offer, 'Pack size (ug)': float(size), 'Packs needed': count,
                        'Total quantity (ug)': float(size * count), 'Total price': str(price * count),
                        'In stock': offer.get('Availability') == 'InStock'})
    return results
