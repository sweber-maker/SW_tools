"""Optional regression comparison using user-owned fixture files outside the repository."""
import argparse, io, json, time
from pathlib import Path
import openpyxl
from engine import load_engine

def compare(source,expected,notebook=None):
    n=load_engine(notebook) if notebook else load_engine();started=time.monotonic()
    kind,outputs=n['process_one'](Path(source).read_bytes(),Path(source).name)
    results={'input_kind':kind,'outputs':[{'format':label,'rows':count,'warnings':len(issues)} for label,content,count,issues,notes in outputs]}
    blob=next(content for label,content,*_ in outputs if label=='v3.1')
    w=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
    reference=openpyxl.load_workbook(expected,read_only=True,data_only=True)
    def designs(sheet,start):
        return {row[2]:row[:19] for row in sheet.iter_rows(min_row=start,max_col=19,values_only=True) if row[2]}
    actual=designs(w['Sequence'],4 if w['Sequence']['A1'].value=='V3.1' else 3);wanted=designs(reference['Sequence'],4)
    results['v3_designs_matched_by_name']=len(actual.keys()&wanted.keys())
    results['v3_sequence_cell_differences']=sum(a!=b for name in actual.keys()&wanted.keys() for a,b in zip(actual[name],wanted[name]))
    actual_order={(r,c):w['Order Details'].cell(r,c).value for r in range(3,18) for c in (2,3)}
    results['v3_order_input_cell_differences']=sum(v!=reference['Order Details'].cell(r,c).value for (r,c),v in actual_order.items())
    results['v3_template_tabs_match']=w.sheetnames==reference.sheetnames
    results['v3_instruction_row_preserved']=w['Sequence']['A1'].value==reference['Sequence']['A1'].value
    results['elapsed_seconds']=round(time.monotonic()-started,2)
    w.close();reference.close();return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('expected');p.add_argument('--notebook',type=Path);a=p.parse_args()
    result=compare(a.source,a.expected,a.notebook)
    Path(__file__).with_name((a.notebook.stem if a.notebook else 'Twist_Unified_Intake_Converter_v2.0')+'_example_results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
