"""Native Colab interface: no tunnels or local installation required by users."""
import base64
import uuid
from pathlib import Path
from IPython.display import HTML, JSON, display, clear_output
import ipywidgets as widgets
from service import report, excel, batch, output_name


def show():
    from google.colab import output
    from google.colab import files
    display(HTML('<h2>Antigen Lookup · v1.01</h2><p>Explicit manufacturer fields and offers only. Review source evidence. No catalog search, PDF parsing, or guaranteed access to vendor sites. Workbook quantities include two runs; epitope binning is off.</p>'))
    url = widgets.Text(description='Product URL:', layout=widgets.Layout(width='95%'))
    catalog = widgets.Text(description='Catalog #:')
    assay = widgets.Dropdown(options=['BLI','SPR'], description='Format:')
    count = widgets.BoundedIntText(value=96, min=1, max=100000, description='Antibodies:')
    mw = widgets.FloatText(value=0, description='MW (kDa):')
    oligomer = widgets.Dropdown(options=[('Unknown',None),('Monomer',1),('Dimer / Fc dimer',2),('Trimer',3)], description='Assembly:')
    basis = widgets.Dropdown(options=[('Monomer MW','monomer'),('Assembly MW','assembly')], description='MW basis:')
    button = widgets.Button(description='Look up product', button_style='primary')
    result = widgets.Output()
    def settings(): return dict(format=assay.value, antibodies=count.value, mw_kda=mw.value or None, oligomer=oligomer.value, mw_basis=basis.value)
    def run(_):
        button.disabled = True
        with result:
            clear_output()
            try:
                data = report(url.value, catalog=catalog.value, **settings())
                import pandas as pd
                for flag in data['Review flags']: print(flag['Warning'])
                for sheet in ['Intake','Calculation','Offers','Purchase options','Evidence']:
                    print(sheet); display(pd.DataFrame(data[sheet]))
                path = Path('/content/antigen_lookup_v1.01.xlsx'); path.write_bytes(excel(data)); files.download(str(path))
            except Exception as e: print(str(e))
        button.disabled = False
    button.on_click(run)
    display(widgets.VBox([url,catalog,assay,count,mw,oligomer,basis,button,result]))
    display(HTML('<p>Batch CSV/XLSX: required URL column; optional Catalog, MW_kDa, Oligomer (1/2/3), MW_basis (monomer/assembly), Format, Antibodies. Uploaded files process automatically. Unknown MW/assembly leaves quantity blank.</p>'))
    identifier = 'antigen_' + uuid.uuid4().hex
    def callback(name, encoded):
        try:
            content = batch(name, base64.b64decode(encoded, validate=True), **settings())
            return JSON({'name':output_name(name),'data':base64.b64encode(content).decode()})
        except Exception as e: return JSON({'error':str(e)})
    output.register_callback(identifier+'.lookup', callback)
    markup = Path(__file__).with_name('upload.html').read_text()
    display(HTML(markup.replace('__HOST_ID__',identifier).replace('__CALLBACK__',identifier+'.lookup')))
