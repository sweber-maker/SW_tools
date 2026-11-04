# Unified intake converter — uploaded v2.0 baseline

The notebook is preserved **byte for byte as uploaded**. This is a tested baseline, not a replacement for the existing v1.03 converter. No conversion bugs were patched in this import. Future fixes should receive a new version (for example, 2.01), while retaining this upload and its test evidence.

## Test results

**51 automated tests: 37 passed, 14 failed, 0 errors, 0 skipped.** All 12 EC variants and all four supported routes executed successfully. See [test report](Twist_Unified_Intake_Converter_v2.0_test_report.md), [machine-readable outcomes](Twist_Unified_Intake_Converter_v2.0_test_results.json), and [full log](Twist_Unified_Intake_Converter_v2.0_test_log.txt).

The earlier 258-design input was also converted. All 258 v3.1 sequence records matched the supplied expected output, but four Order Details inputs differed and template structure was lost. See [example results](Twist_Unified_Intake_Converter_v2.0_example_results.json).

## Run the tests

From the repository root:

```sh
python -m pip install -r unified_converter/requirements.txt
python unified_converter/run_tests.py
```

The runner exits with status **1** while regression failures remain. Failed checks are ordinary failures, not skipped or marked as expected failures. It updates the versioned JSON and text reports. It loads the notebook's embedded assets and engines unchanged; Colab installation/upload/download statements are not executed.

Optional comparison against your own v4.2 input and expected v3.1 output:

```sh
python unified_converter/check_example.py 'input.xlsx' 'expected.xlsx'
```

This comparison records observations (including differences); its completion does not mean the workbooks match. User source/example files remain outside the repository.

## Colab

The original notebook installs openpyxl, then calls Colab's native uploader for multiple XLSX/CSV inputs and automatically downloads a combined ZIP. The native UI was **not tested in a live Colab session**. This upload does not include the hidden-code drop zone from v1.03. Its output names also do not yet meet the repository's source-name + `_converted` + release-version preference.
