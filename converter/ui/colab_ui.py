"""Clean Colab entry point; converter namespace is supplied by the notebook bootstrap."""
import html
from pathlib import Path
from IPython.display import display, HTML
import ipywidgets as widgets
from google.colab import files


def uploaded_items(value):
    """Support both ipywidgets 7 (mapping) and 8 (tuple) payloads."""
    if isinstance(value, dict):
        return [(name, bytes(item['content'])) for name, item in value.items()]
    return [(item['name'], bytes(item['content'])) for item in value]


def show_converter(converter, output_dir='/content/converted'):
    display(HTML('''<div style="font-family:Arial,sans-serif;margin:8px 0 16px">
    <h2 style="margin:0 0 8px">Antibody form converter</h2>
    <div>v4.2 → v3.1 · Version 1.02</div>
    <p>Select one or more Excel files. Conversion starts automatically.</p></div>'''))
    picker=widgets.FileUpload(accept='.xlsx', multiple=True, description='Choose files',
        layout=widgets.Layout(width='240px',height='44px'),button_style='primary')
    results=widgets.VBox()

    def handle(change):
        items=uploaded_items(change['new'])
        if not items: return
        picker.disabled=True
        rows=[]
        try:
            for name,blob in items:
                status=widgets.HTML(value=f'Converting {html.escape(name)}…')
                rows.append(status); results.children=tuple(rows)
                try:
                    if not name.lower().endswith('.xlsx'):
                        raise ValueError('Please choose an .xlsx workbook.')
                    archives=converter({name:blob},output_dir)
                    archive=archives[0]
                    status.value=f'<b>✓ {html.escape(name)}</b><br>Ready. The ZIP includes your workbook and review report.'
                    download=widgets.Button(description='Download ZIP',button_style='success',
                        tooltip=archive.name,layout=widgets.Layout(width='180px'))
                    download.on_click(lambda _,p=str(archive): files.download(p))
                    rows.append(download)
                except Exception as exc:
                    status.value=f'<b>{html.escape(name)}</b><br>{html.escape(str(exc))}'
                results.children=tuple(rows)
        finally:
            picker.disabled=False
            # Reset so choosing the same files again triggers conversion.
            picker.unobserve(handle,names='value')
            picker.value={} if isinstance(picker.value,dict) else ()
            picker.observe(handle,names='value')
    picker.observe(handle,names='value')
    display(picker,results)
    return picker,results
