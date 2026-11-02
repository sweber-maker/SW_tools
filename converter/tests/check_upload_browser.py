"""Browser smoke test with the Colab kernel bridge mocked locally."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(accept_downloads=True)
    page.add_init_script('')
    page.set_content('''<script>
window.calls=[];
window.google={colab:{kernel:{invokeFunction:async function(callback,args){
 calls.push(args[0]);
 if(args[0]==='broken.xlsx')return {data:{'application/json':{error:'Bad workbook'}}};
 return {data:{'application/json':{name:args[0].replace('.xlsx','_converted_v1.03.zip'),data:btoa('zip bytes')}}};
}}}};
</script>'''+Path(__file__).parents[1].joinpath('ui/upload.html').read_text().replace('__HOST_ID__','test').replace('__CALLBACK__','test.convert'))
    with page.expect_file_chooser() as chooser:
        page.get_by_role('button',name='Choose files',exact=True).click()
    chooser.value.set_files([{'name':'picker.xlsx','mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':b'x'}])
    page.get_by_role('link',name='Download ZIP').wait_for()
    assert page.evaluate('window.calls')==['picker.xlsx']
    # Actual browser drag/drop event with two files plus one failure.
    page.locator('.dropzone').evaluate('''zone=>{
 const transfer=new DataTransfer();
 for(const name of ['first.xlsx','broken.xlsx','second.xlsx'])transfer.items.add(new File(['input'],name));
 zone.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));
}''')
    page.get_by_text('Could not convert: Bad workbook',exact=True).wait_for()
    page.wait_for_function("document.querySelectorAll('.results a').length===2")
    assert page.evaluate('window.calls')==['picker.xlsx','first.xlsx','broken.xlsx','second.xlsx']
    with page.expect_download() as download:
        page.get_by_role('link',name='Download ZIP').first.click()
    assert download.value.suggested_filename=='first_converted_v1.03.zip'
    assert page.locator('.dropzone').get_attribute('aria-disabled')=='false'
    browser.close()
    print('PASS: file picker, multi-file drop, per-file error recovery, ZIP download filename')
