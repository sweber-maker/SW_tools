# Summit final-sequence reference

The private final CSV matches all **33** construct names, insert DNA sequences, and vector + insertion-site combinations from the Summit fallback list. All 33 insert/construct length fields match the supplied DNA lengths, and each insert occurs exactly once in its corresponding full construct. DNA is unambiguous A/C/G/T. There are no missing or extra construct names.

Use **Insert sequence** for comparison to the simple list. **Construct sequence** includes the vector backbone and is validated separately. The metadata implies a 58-base vector region is replaced in each construct; no independent vector reference was supplied to validate the remaining backbone sequence.

This adds a reference test only. It does not change the converter, its assembly rules, or its supported CSV upload formats. This vendor-final CSV schema is a reference fixture, distinct from the paired Sequence Download CSV accepted by the converter.

The metadata/hashes are in `summit_final_reference.json`; sanitized outcomes are in `Twist_Unified_Intake_Converter_v2.03_summit_reference_results.json`. Neither the raw final CSV nor customer DNA is stored in GitHub.

To repeat using the private fixtures:

```sh
python unified_converter/check_summit_reference.py 'Summit workbook.xlsx' 'Final Sequence.csv' --report /private/output/comparison.json
python -m unittest discover -s unified_converter/reference_tests -v
```

The real-fixture checker verifies both registered input hashes, regenerates the fallback through the notebook engine, checks that normal outputs are absent and compares by unique construct name. It returns a failing exit status for any mismatch. Eight synthetic tests exercise mismatched insert/site/name/length, duplicated inserts/names and missing columns. This validates identity and metadata, not reading frame or biological function.
