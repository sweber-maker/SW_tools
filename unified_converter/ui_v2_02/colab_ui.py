"""Colab upload UI with a native file picker and explicit multiple-file drop zone."""
import base64
import csv
import io
import zipfile
from pathlib import Path
import uuid
from IPython.display import HTML, JSON, display
from google.colab import output


def convert_upload(name, encoded, converter, output_dir):
    """One callback per file keeps a batch from becoming one large request."""
    try:
        if not name.lower().endswith(('.xlsx','.csv')):
            raise ValueError('Please choose an .xlsx workbook or paired-chain .csv file.')
        blob=base64.b64decode(encoded,validate=True)
        archive=converter({name:blob},output_dir)[0]
        with zipfile.ZipFile(archive) as bundle:
            report_name=next(name for name in bundle.namelist() if name.endswith('_report.csv'))
            statuses=list(csv.DictReader(io.StringIO(bundle.read(report_name).decode('utf-8-sig'))))
        if any(row['Status']=='FAILED' for row in statuses):
            message='Conversion failed. Download the ZIP for the validation report; no incomplete DNA table is exported.'
        elif any(row['Status']=='REJECTED' for row in statuses):
            message='Normal conversions rejected (extra constructs). ZIP contains the DNA-only fallback and assembly audit; review any warnings.'
        else:message='Ready. ZIP includes converted workbooks and review reports.'
        return {'name':archive.name,'data':base64.b64encode(archive.read_bytes()).decode('ascii'),'message':message}
    except Exception as exc:
        return {'error':str(exc)}


def show_converter(converter, output_dir='/content/converted'):
    identifier='converter_'+uuid.uuid4().hex
    callback=identifier+'.convert'
    output.register_callback(callback,lambda name,data:JSON(convert_upload(name,data,converter,output_dir)))
    markup=Path(__file__).with_name('upload.html').read_text()
    display(HTML(markup.replace('__HOST_ID__',identifier).replace('__CALLBACK__',callback)))
    return callback
