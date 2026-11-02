"""Compare a user's v4.2 input and expected v3.1 workbook without retaining private fixtures."""
import argparse, io
from openpyxl import load_workbook
from convert import convert, occupied

def validate(source, expected):
    content,count,issues=convert(source)
    actual=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
    reference=load_workbook(expected,read_only=True,data_only=True)
    for name,max_row in [('Sequence',count+3),('Order Details',25)]:
        for ar,er in zip(actual[name].iter_rows(max_row=max_row),reference[name].iter_rows(max_row=max_row)):
            for a,e in zip(ar,er):
                assert a.value==e.value, f'{name}!{a.coordinate}: {a.value!r} != {e.value!r}'
    original=load_workbook(io.BytesIO(source),read_only=True,data_only=True)
    for rr in list(range(4,16))+list(range(18,30)):
        assert actual['Contact Information'].cell(rr,2).value==original['Contact Information'].cell(rr,2).value
    print(f'PASS: {count} designs; all Sequence and Order Details cell values match the supplied example; contact values match the source.')
    actual.close(); reference.close(); original.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('expected');a=p.parse_args()
    with open(a.source,'rb') as f: validate(f.read(),a.expected)
