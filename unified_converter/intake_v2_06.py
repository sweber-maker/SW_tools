"""Input-only row-1 Sequence intake (22-column v4.2-like layout)."""
import io
import re
import openpyxl

MARKER='__sw_tools_input'
FORMAT='sequence_intake'
def norm(value):return re.sub('[^a-z0-9]','',str(value or '').lower())

def identify(workbook):
    if MARKER in workbook.sheetnames and workbook[MARKER]['A1'].value==FORMAT:return True
    if 'Antibody Designs' in workbook.sheetnames:return False
    if 'Sequence' not in workbook.sheetnames:return False
    sheet=workbook['Sequence']
    expected={3:{'iggname','antibodyname'},4:{'purification'},7:{'iggisotype','isotype'},9:{'vhname','construct1name'},10:{'vhvectornameinsertionsitename','vectornameinsertionsitename'},15:{'vhvdjsequencednaoraa','construct1sequencednaoraa'},16:{'vlname','construct2name'},17:{'vlvectornameinsertionsitename','vectornameinsertionsitename'},22:{'vlsequencednaoraa','vlvjsequencednaoraa','construct2sequencednaoraa'}}
    available={norm(cell.value) for cell in next(sheet.iter_rows(max_row=1,max_col=37))}
    return all(any(value in available for value in values) for values in expected.values())

def normalize(blob):
    if not isinstance(blob,(bytes,bytearray)) or not bytes(blob).startswith(b'PK'):return blob,False
    source=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
    try:
        if MARKER in source.sheetnames and source[MARKER]['A1'].value==FORMAT:return blob,True
        if not identify(source):return blob,False
        sheet=source['Sequence']
        positions={1:{'plate'},2:{'well'},3:{'iggname','antibodyname'},4:{'purification'},5:{'histagselection'},6:{'histagsequence'},7:{'iggisotype','isotype'},8:{'lightchainlambdaorkappa','lightchainor'},9:{'vhname','construct1name'},10:{'vhvectornameinsertionsitename','vectornameinsertionsitename'},11:{'vhkozaksettings','vhkozaksetting','kozaksetting'},12:{'vhkozaksequencedna','kozaksequencedna'},13:{'vhleadersetting','leadersetting'},14:{'vhleadersequencedna','vhleadersequencednaoraa','leadersequencednaoraa'},15:{'vhvdjsequencednaoraa','construct1sequencednaoraa'},16:{'vlname','construct2name'},17:{'vlvectornameinsertionsitename','vectornameinsertionsitename'},18:{'vlkozaksettingsdna','vlkozaksettings','vlkozaksetting','kozaksetting'},19:{'vlkozaksequencedna','kozaksequencedna'},20:{'vlleadersetting','leadersetting'},21:{'vlleadersequencedna','vlleadersequencednaoraa','leadersequencednaoraa'},22:{'vlsequencednaoraa','vlvjsequencednaoraa','construct2sequencednaoraa'}}
        for column,allowed in positions.items():
            if norm(sheet.cell(1,column).value) not in allowed:
                raise ValueError(f'Sequence intake header {openpyxl.utils.get_column_letter(column)}1 does not match the supported column layout; no positional guess applied')
        if sheet.max_column>37:
            for row in sheet.iter_rows(min_row=2,min_col=38,values_only=True):
                if any(value is not None and str(value).strip() for value in row):
                    raise ValueError('Sequence intake contains populated fields beyond the supported construct layout; manual review required')
        dest=openpyxl.Workbook();designs=dest.active;designs.title='Antibody Designs'
        headers=next(sheet.iter_rows(max_row=1,max_col=37,values_only=True))
        for column,value in enumerate(headers,1):designs.cell(3,column,value)
        designs.cell(3,15,'Construct 1 Sequence (DNA or AA)');designs.cell(3,22,'Construct 2 Sequence (DNA or AA)')
        for target_row,row in enumerate(sheet.iter_rows(min_row=2,max_col=37,values_only=True),4):
            for column,value in enumerate(row,1):
                if value is not None:
                    cell=designs.cell(target_row,column,value)
                    if isinstance(value,str):cell.data_type='s'
        marker=dest.create_sheet(MARKER);marker['A1']=FORMAT;marker['A2']='Sequence';marker['A3']=2;marker.sheet_state='hidden'
        result=io.BytesIO();dest.save(result);dest.close()
        return result.getvalue(),True
    finally:source.close()

def validate_normal_rows(blob):
    workbook=openpyxl.load_workbook(io.BytesIO(blob),read_only=True,data_only=True)
    try:
        for row_number,row in enumerate(workbook['Antibody Designs'].iter_rows(min_row=4,max_col=37,values_only=True),2):
            name=row[2];first=row[14];second=row[21]
            if name and not first:raise ValueError(f'Sequence row {row_number}: named design has no VH sequence')
            if row[15] and not second:raise ValueError(f'Sequence row {row_number}: named VL construct has no VL sequence')
            if not name and (first or second):raise ValueError(f'Sequence row {row_number}: sequence has no antibody name')
    finally:workbook.close()
