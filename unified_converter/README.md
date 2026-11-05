# Unified intake converter — version 2.03

[Open 2.03 in Google Colab](https://colab.research.google.com/github/sweber-maker/SW_tools/blob/main/unified_converter/Twist_Unified_Intake_Converter_v2.03.ipynb)

Click ▶ once, then drag one or multiple XLSX/CSV files into the upload area or click **Choose files**. Each upload gets its own ZIP named `original upload_converted_v2.03.zip`; every generated file inside retains that source name and release version. The notebook embeds all code and templates.

## Real-file regression set

[The 13-file customer case list](customer_cases.json) now covers 11 v4.2 forms and two existing v3.1 forms. **All 13 pass** their expected conversion/rejection checks. The initial 12 files retain 1,330 normal design rows, including the duplicate IL2 upload. The Summit file has nine three-construct and three two-construct rows: both normal formats are rejected and a separate 33-construct DNA list is verified, with every supplied Kozak/leader prefix already present. See the [customer results](Twist_Unified_Intake_Converter_v2.03_customer_test_results.json) and [release report](Twist_Unified_Intake_Converter_v2.03_test_report.md).

The tool now maps no-physical-shipment and Yes/No sterile-filtration choices correctly, respects Micronic tube volume, repairs existing v3.1 inputs through template normalization, and splits mixed one/two-chain EC inputs by chain count. Existing v3.1 sources receive a normalized v3.1 output only.

```sh
python unified_converter/run_customer_tests.py --fixtures-dir /path/to/private/workbooks --output-dir /path/to/private/outputs
```

The raw customer files remain private external fixtures; only filenames, hashes and sanitized outcomes are stored in GitHub. Missing fixtures fail rather than being silently counted as passing.

## Normal outputs

- v4.2 input → template-preserving **v3.1** and **EC_upload**.
- Paired Sequence Download CSV / supported legacy XLSX → v4.2, v3.1 and EC_upload.
- EC input → v4.2.
- Existing v3.1 input → normalized v3.1 (including existing service selections/notes).

EC_upload means the EC workbook format. The tool selects the applicable one of the 12 EC template variants; it does not create 12 alternative orders for each input. All 12 variants are tested.

The v3.1 fixes from 2.01 remain: six template tabs, instruction rows, styles and formulas; source-only Order Details; contacts; source isotypes and plate/well values; custom sequences retained. Dropdown controls are removed. Review scientific choices and warnings before ordering.

## Any third or fourth construct: reject normal conversion

The scanner checks **every v4.2 row**, including rows lacking an antibody name or first sequence. Populated third/fourth construct fields reject both v3.1 and EC_upload for the **entire workbook**. Low-level standard conversion entry points also enforce the rule. Third/fourth construct placeholders alone do not count as populated constructs. A declared three/four-part transfection ratio also prevents normal conversion. A two-part ratio does not imply extra constructs and is reported as unrepresented in v3.1.

The bundled template's known blank AD formula is ignored when its source vector is blank. Cached formula DNA counts as occupied; an unknown unresolved formula is not assumed empty.

## Separate DNA-only fallback

For a rejected v4.2 workbook, the ZIP contains a separate `*_DNA_constructs.xlsx` when DNA validation succeeds. It has exactly three columns:

**Name | Sequence | Vector Name**

It includes every populated construct block from every row, including one/two-construct rows in a mixed workbook. An audit JSON records source rows, construct indices, assembly actions, warnings and errors. Both normal outputs remain marked **REJECTED**; the fallback is never presented as a successful v3.1/EC_upload conversion.

DNA assembly checks:

- Use literal A/C/G/T DNA; normalize whitespace and case. Never reverse translate protein or resolve ambiguous bases by guessing.
- If the full Kozak + leader prefix is already present, retain the insert unchanged (including a preceding cloning overhang).
- If the insert already starts with the leader, add only the missing Kozak. If it starts with the Kozak, add only the missing leader.
- If neither prefix is present, concatenate Kozak + leader + insert. Do not trim short coincidental base overlaps.
- Do not duplicate a Kozak already included in the separately supplied leader field.
- Block uncertain partial/internal/reversed matches for manual DNA review instead of editing a coding sequence by guesswork. An internal Kozak motif alone is not treated as a verified 5-prime signal.
- Missing separate Kozak/leader data is reported as unverifiable; supplied DNA is retained without inventing missing components. Missing vector names remain blank with a warning; absent construct names are derived and reported. Duplicate names are retained and flagged, not silently deduplicated.

If any construct cannot be validated/assembled, **no partial DNA table is exported**. The downloadable ZIP contains the failure report/audit instead. A transfection ratio declaring a different number of constructs also blocks the fallback. Alphabet validation does not establish reading frame, signal-peptide function or biological suitability; a protein composed only of A/C/G/T letters cannot be distinguished from DNA by alphabet alone.

The UI explicitly labels normal-conversion rejection and failed DNA checks. One failed upload does not stop the other files in a batch.

## Reproduce validation

```sh
python -m pip install -r unified_converter/requirements.txt
python unified_converter/run_v2_03_tests.py
```

The complete run retains three previously documented CSV/EC failures as ordinary failures, so it exits nonzero. They concern incomplete CSV records being skipped, mixed CAC/CAT His-tag length counting, and underscore-separated tube filename hints. Incomplete CSV records can affect downstream outputs; review input completeness before ordering. They are outside the new extra-construct/fallback changes.

The synthetic suite has **113 tests: 110 passed and 3 known failures**. See [2.03 test report](Twist_Unified_Intake_Converter_v2.03_test_report.md), [machine-readable results](Twist_Unified_Intake_Converter_v2.03_test_results.json), [full log](Twist_Unified_Intake_Converter_v2.03_test_log.txt).

```sh
python unified_converter/check_example.py 'input.xlsx' 'expected.xlsx' --notebook unified_converter/Twist_Unified_Intake_Converter_v2.03.ipynb
```

The comparison records observations; its exit status alone does not establish zero differences. User source/example workbooks stay outside the repository.

Optional browser check (Playwright + Chromium): `python unified_converter/tests_v2_03/check_upload_browser.py`. Local picker, drag/drop, per-file error handling and ZIP download checks mock the Colab kernel bridge; live Colab and native Microsoft Excel visual rendering still need a user-browser check.

## Source and history

Build the self-contained release with `python unified_converter/build_v2_03.py`. Sources: `constructs_v2_02.py`, `routing_v2_03.py`, `runtime_v2_03.py`, `v3_engine_v2_03.py`, `ui_v2_03/`. Increment the version for future releases.

The original v2.0 upload and baseline, v2.01 repair, v2.02 fallback release, and earlier standalone releases remain available. Run `run_tests.py` for the original baseline or `run_v2_01_tests.py` for 2.01. Published notebooks are retained unchanged.

## Summit final CSV reference

The [separate private-reference check](SUMMIT_REFERENCE.md) confirms that all 33 Summit fallback inserts match the supplied final-sequence CSV exactly, including names and vector/insertion-site metadata. It compares Insert sequence, not the full vector Construct sequence. This is reference validation, not a change to supported conversion routes.
