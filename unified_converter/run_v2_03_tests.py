"""Run release checks, keeping remaining non-v3 defects visible with a failing exit status."""
import argparse, contextlib, datetime, hashlib, io, json, sys, unittest
from pathlib import Path
import openpyxl
from run_tests import RecordedResult

ROOT=Path(__file__).resolve().parent

def flatten(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite): yield from flatten(test)
        else: yield test

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--v3-only',action='store_true');args=parser.parse_args()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests_v2_03'))
    if args.v3_only:suite=unittest.TestSuite(t for t in flatten(suite) if '.V3Tests.' in t.id())
    log=io.StringIO()
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(suite)
    notebook=ROOT/'Twist_Unified_Intake_Converter_v2.03.ipynb'
    report={'notebook':notebook.name,'sha256':hashlib.sha256(notebook.read_bytes()).hexdigest(),
            'run_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version.split()[0],'openpyxl':openpyxl.__version__,
            'scope':'v3-only' if args.v3_only else 'full-release','tests_run':result.testsRun,
            'passed':sum(o['status']=='passed' for o in result.outcomes),'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'outcomes':result.outcomes,'limits':'Synthetic workbook fixtures. Live Google Colab not exercised; separate browser test mocks only the Colab kernel bridge.'}
    suffix='_v3' if args.v3_only else ''
    base=ROOT/f'Twist_Unified_Intake_Converter_v2.03{suffix}'
    Path(str(base)+'_test_results.json').write_text(json.dumps(report,indent=2))
    Path(str(base)+'_test_log.txt').write_text(log.getvalue())
    print(f"{report['scope']}: {report['tests_run']} tests, {report['passed']} passed, {report['failed']} failed, {report['errors']} errors, {report['skipped']} skipped")
    sys.exit(0 if result.wasSuccessful() else 1)
