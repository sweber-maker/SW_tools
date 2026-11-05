# 2.06 — row-1 Sequence intake, EC_upload only

The `incyte_test.xlsx` example uses a 22-column `Sequence` table with headers on row 1 and records beginning on row 2. Its columns align with the first two constructs of v4.2, including purification, isotype, vectors, Kozak/leader settings and literal sequences.

The format is detected by header content, independent of filename. Its normal route emits **EC_upload only**: no v3.1, v4.2 or copy of the input format is exported, and no reverse conversion to this format is implemented. A temporary in-memory normalization reuses the existing EC parser/signal safeguards; the source workbook is never overwritten or returned as an output.

## Format handling

- Column labels are normalized for case/punctuation and checked against the supported layout. An unsupported/reordered column layout fails explicitly rather than guessing a positional mapping.
- All names, primary DNA/AA sequences, vector identities, and literal Kozak/leader DNA are carried into EC. Vector spelling is matched to the template's equivalent dropdown text; nucleotides are not fuzzy-corrected.
- Missing antibody names or named VH/VL constructs without their sequences fail rather than silently disappearing.
- Source plate/well values are preserved when supplied. Blank coordinates receive the existing standard 96-well EC map.
- Third/fourth constructs still reject every normal output. The established DNA-only fallback remains available when all DNA checks pass. New-input fallback audits use the original `Sequence` row numbers.
- Existing v4.2, v3.1, EC and supported legacy/paired CSV routes keep their previous behavior.
- Submission Instructions and hidden validation documentation are reference data, not commands. Signal instructions without sufficient DNA evidence remain review items; no protein reverse translation is added.

## Actual input validation

The supplied private fixture contains 100 paired antibodies with Protein A purification. Its output is one EC_upload workbook with 100 records and 200 unchanged primary chain sequences. Tests verify all names, normalized vector identities, 400 literal signal-DNA fields, two generated plate maps, 100 unique valid plate/well coordinates, ZIP integrity and source/version-based filenames. No v3.1 or v4.2 artifact is present.

The raw workbook and resulting sequences stay outside GitHub. `customer_cases.json` registers its filename/hash and expected input-only behavior as case 15.

## Tests

- 17 focused input-format tests pass: filename-independent detection, exact mapping, EC-only output, invalid/missing data, unsupported column order, existing-format compatibility, batch recovery, extra constructs/fallback and source-row diagnostics.
- All 15 private real-file cases pass.
- All 18 signal tests pass, including the 12 EC template variants; all 10 small-launcher checks pass.
- The 33-construct Summit final reference remains identical.

The three previously documented shared CSV/EC limitations remain (incomplete CSV rows, mixed CAC/CAT His-tag counting and underscore-separated tube hints). This release does not claim to fix them. Native Excel/Colab browser rendering is not independently validated; the workbook structure, actual values, runtime startup path and local upload bridge are tested.

```sh
python -m unittest discover -s unified_converter/intake_tests -v
python -m unittest discover -s unified_converter/signal_tests -v
python -m unittest discover -s unified_converter/launcher_tests -v
python unified_converter/run_customer_tests.py --notebook START_HERE.ipynb --fixtures-dir /private/workbooks --output-dir /private/outputs
```

Build with `python unified_converter/build_launcher_v2_06.py`. The small launcher and release ZIP retain checksum verification; no customer workbook is included in the runtime package.
