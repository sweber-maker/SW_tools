# Version 2.04 — small Colab launcher

Use the root [START_HERE.ipynb](../START_HERE.ipynb), or [open it directly in Colab](https://colab.research.google.com/github/sweber-maker/SW_tools/blob/main/START_HERE.ipynb).

The 2.03 notebook is 782,084 bytes and contains a 767,785-character source line. The replacement is 3,542 bytes with a longest source line of 129 characters. The large embedded literal was a plausible cause of the reported immediate blank page; the user's logged-in Colab session was not available to reproduce that browser failure.

The notebook is now only a launcher. After ▶ it downloads a 2.04 runtime ZIP from the immutable release tag, checks its SHA-256, installs the normal dependencies and opens the existing multi-file picker/drop area. The template/code payload is processed on the Python runtime rather than in the browser editor. Cell IDs are provided and the notebook passes strict nbformat validation. Network/checksum/startup errors produce visible output after ▶.

The runtime package derives from the frozen 2.03 notebook. A test compares every source asset and confirms only the two converter version constants change; mapping, sequence assembly and rejection policies are unchanged. UI wording identifies version 2.04. Package URLs use tag `unified-v2.04`; the notebook verifies the package hash before running its code. Internet access to GitHub and PyPI is required at startup.

## Validation

- 10 launcher checks pass: notebook schema, size/line limits, identical root/archive notebooks, package hashes, unchanged converter logic, actual bootstrap execution with upload controls, visible network/checksum failures, extraction-path checks, and fresh controls on restart.
- Actual bootstrap code is executed locally using the real ZIP; the HTTP response, pip subprocess and Colab display/callback bridge are mocked. Live Colab rendering is not claimed.
- All 13 private real-workbook cases pass against the launcher package, including Summit's 33 DNA constructs and rejection of normal outputs.
- All 33 Summit inserts still match the private final-sequence CSV exactly, including names and vector/insertion-site metadata.
- The three previously documented shared CSV/EC defects remain; this packaging repair does not claim to fix them.

See [release validation](releases/unified_v2.04_validation.json), [customer results](Twist_Unified_Intake_Converter_v2.04_customer_test_results.json), and [Summit reference results](Twist_Unified_Intake_Converter_v2.04_summit_reference_results.json).

## Repeat checks

```sh
python -m pip install -r unified_converter/requirements.txt 'nbformat>=5.10,<6'
python -m unittest discover -s unified_converter/launcher_tests -v
python unified_converter/run_customer_tests.py --notebook START_HERE.ipynb --fixtures-dir /private/workbooks --output-dir /private/outputs
```

Missing customer fixtures fail their checks rather than being silently counted as passing. Test catalogs and sanitized results remain in GitHub; raw customer workbooks and output DNA do not.

Build with `python unified_converter/build_launcher_v2_04.py`. The ZIP is deterministic and contains only versioned runtime sources/assets; no private regression fixtures are bundled. Root and versioned notebook copies must remain identical. Publish both the ZIP and release tag together; a checksum-matching package is required for startup. Previous notebooks remain unchanged.
