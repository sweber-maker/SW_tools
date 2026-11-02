"""Streamlit interface for Antigen Lookup 1.01."""
import streamlit as st
from service import report, excel, batch, output_name

st.set_page_config(page_title='Antigen Lookup 1.01', page_icon='🧬', layout='wide')
st.title('Antigen Lookup · v1.01')
st.caption('Manufacturer evidence, two-run BLI/SPR quantities, and product-linked price/stock. Review extracted candidates before ordering or experimental use.')
with st.sidebar:
    format = st.selectbox('Assay format', ['BLI','SPR'])
    antibodies = st.number_input('Number of antibodies', min_value=1, value=96, step=1)
    st.info('BLI: 96 antibodies/batch. SPR: 372/batch. Workbook quantities already include 2 runs. Epitope binning is off. Partial batches use a full batch allowance.')
    mw = st.number_input('Manufacturer MW (kDa); 0 = unknown', min_value=0.0, value=0.0)
    oligomer = st.selectbox('Confirmed oligomeric condition', ['Unknown','Monomer','Dimer / Fc dimer','Trimer'])
    basis = st.selectbox('MW describes', ['One monomer / chain','Full assembled oligomer'])
settings = dict(format=format, antibodies=antibodies, mw_kda=mw or None,
                oligomer={'Unknown':None,'Monomer':1,'Dimer / Fc dimer':2,'Trimer':3}[oligomer],
                mw_basis='monomer' if basis.startswith('One') else 'assembly')
st.warning('This release reads explicit labeled HTML fields and product-linked structured offers. It does not yet search catalogs, parse CoAs/PDFs, or reliably extract values from free text or JavaScript-only pages. A missing result does not establish absence.')
single, multiple = st.tabs(['Product lookup','Batch files'])
with single:
    with st.form('lookup'):
        url = st.text_input('Direct manufacturer product URL')
        catalog = st.text_input('Catalog number (recommended)', placeholder='IL0-H5243')
        go = st.form_submit_button('Look up product')
    if go:
        try:
            with st.spinner('Reading manufacturer source…'): st.session_state.report = report(url, catalog=catalog, **settings)
        except ValueError as e: st.error(str(e))
    if 'report' in st.session_state:
        result = st.session_state.report
        for w in result['Review flags']: st.warning(w['Warning'])
        for sheet in ['Intake','Calculation','Offers','Purchase options','Evidence']:
            st.subheader(sheet)
            if result[sheet]: st.dataframe(result[sheet], hide_index=True)
            else: st.caption('Not available / not confirmed.')
        st.caption('Purchase options repeat one pack size at a time; they do not optimize mixed packs. Prices exclude shipping/tax, and stock is a timestamped observation, not a reservation. Re-run lookup after changing inputs.')
        st.download_button('Download Excel report', excel(result), 'antigen_lookup_v1.01.xlsx')
        with st.expander('Retrieved manufacturer text'): st.write(result['Manufacturer text'])
with multiple:
    st.write('CSV/XLSX with URL column. Optional: Catalog, MW_kDa, Oligomer (1/2/3), MW_basis (monomer/assembly), Format (BLI/SPR), Antibodies. Row settings override sidebar defaults. Upload starts processing automatically.')
    uploads = st.file_uploader('Drop files or choose files', type=['csv','xlsx'], accept_multiple_files=True)
    for upload in uploads:
        try:
            data = upload.getvalue()
            key = (upload.name, data, tuple(settings.items()))
            cache = st.session_state.setdefault('batch_reports', {})
            if key not in cache:
                with st.spinner(f'Processing {upload.name}…'): cache[key] = batch(upload.name, data, **settings)
            st.download_button(f'Download {upload.name} results', cache[key], output_name(upload.name), key=upload.file_id)
        except Exception as e: st.error(f'{upload.name}: {e}')
