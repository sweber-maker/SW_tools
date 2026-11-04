"""Record genuine passing/failing baseline checks; preserve a nonzero exit on failure."""
import contextlib, datetime, hashlib, io, json, sys, unittest
import openpyxl
from pathlib import Path

ROOT=Path(__file__).resolve().parent
class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.outcomes=[]
    def addSuccess(self,test):
        super().addSuccess(test);self.outcomes.append({'test':test.id(),'status':'passed'})
    def addFailure(self,test,err):
        super().addFailure(test,err);self.outcomes.append({'test':test.id(),'status':'failed','detail':self._exc_info_to_string(err,test)})
    def addError(self,test,err):
        super().addError(test,err);self.outcomes.append({'test':test.id(),'status':'error','detail':self._exc_info_to_string(err,test)})

if __name__=='__main__':
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    log=io.StringIO()
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(suite)
    notebook=ROOT/'Twist_Unified_Intake_Converter_v2.0.ipynb'
    report={'notebook':notebook.name,'sha256':hashlib.sha256(notebook.read_bytes()).hexdigest(),
            'run_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version.split()[0],'openpyxl':openpyxl.__version__,
            'tests_run':result.testsRun,'passed':sum(o['status']=='passed' for o in result.outcomes),
            'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'outcomes':result.outcomes,'limits':'Synthetic fixtures; Colab UI not executed. Batch wrapper tests mock conversion and redirect only the output path.'}
    (ROOT/'Twist_Unified_Intake_Converter_v2.0_test_results.json').write_text(json.dumps(report,indent=2))
    (ROOT/'Twist_Unified_Intake_Converter_v2.0_test_log.txt').write_text(log.getvalue())
    print(f"{report['tests_run']} tests: {report['passed']} passed, {report['failed']} failed, {report['errors']} errors, {report['skipped']} skipped")
    sys.exit(0 if result.wasSuccessful() else 1)
