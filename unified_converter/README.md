# Unified intake converter — version 2.01

**Version 2.01 fixes the v3.1 regressions in the uploaded v2.0 notebook.** The original upload and its baseline test evidence remain unchanged.

[Open 2.01 in Google Colab](https://colab.research.google.com/github/sweber-maker/SW_tools/blob/main/unified_converter/Twist_Unified_Intake_Converter_v2.01.ipynb)

Click ▶ once, then drop one or multiple XLSX/CSV files into the upload area or click **Choose files**. Each file converts automatically and gets its own ZIP named `original upload_converted_v2.01.zip`. Workbooks, notes, and reports inside include the source filename and release version. The notebook embeds all templates and code; no separate uploads or repository checkout are needed in Colab.

## v3.1 fixes

- Use the supplied six-tab v3.1 template, preserving headers, instructions, styles, merged cells, drawings, formulas, print settings and supporting files. Only list-validation controls are removed.
- Put sequence data on row 4, preserve plate/well positions and supported source isotypes, and retain custom Kozak/leader sequences verbatim.
- Match occupied source Antibody Settings / Order Details selections to v3.1 options. Blank source fields stay blank; notes follow their labels even when source rows are reordered.
- Copy source contact information, retaining separate shipping/billing sections.
- Keep custom vector names when there is no normalized template match. Unrepresented isotypes become `Other, please specify below`, with the original in the warning report; they never become another IgG subclass through fuzzy matching.
- Report the sample-confirmed mini-binder mapping and any inferred choices. Reject named designs lacking a first sequence and unsupported extra constructs.

The EC and v3.1 engine namespaces are isolated to prevent shared settings/functions from changing each other's conversions.

## Validation

**20/20 focused v3.1 tests passed. Full release: 59 tests, 56 passed, 3 failed, 0 errors, 0 skipped.**

The paired 258-design example has zero sequence-cell differences and zero Order Details input differences from the supplied reference, with matching template tabs and instruction rows. Source contacts intentionally follow the input, not the different contacts in the reference workbook. The template/package checks verify style and layout preservation structurally; no native Microsoft Excel visual check was performed.

The three remaining failures are in the unchanged shared CSV/EC logic:

1. An incomplete CSV record can be silently skipped when other complete pairs exist. This can affect any downstream output from that CSV.
2. Mixed CAC/CAT His-tag DNA is undercounted in EC output.
3. A tube hint joined by an underscore in a filename is not recognized; use a separated word such as `input tube.xlsx` pending that fix.

Review warnings and input completeness before ordering. A successful route or row count does not establish scientific correctness. The real example generated 261 v3.1 review items: 258 documented mini-binder mappings, two closest-option mappings, and one unmapped aSEC request. The aSEC request is reported rather than silently discarded. EC warnings are unchanged.

See the [release report](Twist_Unified_Intake_Converter_v2.01_test_report.md), [full results](Twist_Unified_Intake_Converter_v2.01_test_results.json), [focused results](Twist_Unified_Intake_Converter_v2.01_v3_test_results.json), and [example comparison](Twist_Unified_Intake_Converter_v2.01_example_results.json).

## Reproduce checks

From the repository root:

```sh
python -m pip install -r unified_converter/requirements.txt
python unified_converter/run_v2_01_tests.py --v3-only
python unified_converter/run_v2_01_tests.py
```

The full run exits with status 1 while the three known failures remain. They are ordinary failing tests, not skipped or marked expected failures. The focused run exits successfully. Reports retain the tested notebook SHA-256 and dependency versions.

```sh
python unified_converter/check_example.py 'input.xlsx' 'expected.xlsx' --notebook unified_converter/Twist_Unified_Intake_Converter_v2.01.ipynb
```

The example comparison records differences and does not assert that they are zero. User source/example workbooks remain outside this repository.

Optional browser check (requires Playwright and Chromium):

```sh
python unified_converter/tests_v2_01/check_upload_browser.py
```

Picker, multiple-file drop (including CSV), per-file error recovery and named ZIP downloads passed in local Chromium with a mocked Colab kernel bridge. Live Google Colab integration remains a user-browser check.

## Source and builds

`v3_engine.py`, `routing_v2_01.py`, `runtime_v2_01.py`, and `ui/` are reviewable sources for the self-contained notebook. Rebuild with `python unified_converter/build_v2_01.py` and rerun checks after changes. Future releases must increment the version instead of overwriting a published notebook.

The original v2.0 notebook is preserved byte for byte. Its original 51-test baseline (37 passed, 14 failed) remains available in `Twist_Unified_Intake_Converter_v2.0_*` reports. Run it with `python unified_converter/run_tests.py`. The earlier standalone v1.03 converter is also retained.
