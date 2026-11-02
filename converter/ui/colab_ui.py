"""Colab upload UI with a native file picker and explicit multiple-file drop zone."""
import base64
from pathlib import Path
import uuid
from IPython.display import HTML, JSON, display
from google.colab import output


def convert_upload(name, encoded, converter, output_dir):
    """One callback per file keeps a batch from becoming one large request."""
    try:
        if not name.lower().endswith('.xlsx'):
            raise ValueError('Please choose an .xlsx workbook.')
        blob=base64.b64decode(encoded,validate=True)
        archive=converter({name:blob},output_dir)[0]
        return {'name':archive.name,'data':base64.b64encode(archive.read_bytes()).decode('ascii')}
    except Exception as exc:
        return {'error':str(exc)}


def show_converter(converter, output_dir='/content/converted'):
    identifier='converter_'+uuid.uuid4().hex
    callback=identifier+'.convert'
    output.register_callback(callback,lambda name,data:JSON(convert_upload(name,data,converter,output_dir)))
    markup=Path(__file__).with_name('upload.html').read_text()
    display(HTML(markup.replace('__HOST_ID__',identifier).replace('__CALLBACK__',callback)))
    return callback
