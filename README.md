# SW_tools

Personal tools. First tool: **v4.2 → v3.1 antibody form converter, version 1.03**.

## Use in Google Colab

Open `converter/V4.2_to_V3.1_Fast_Batch_Fixed_converted_v1.03.ipynb` in Colab, click ▶ once to start, then drag files into the upload area or use **Choose files** to select one or multiple **v4.2 input workbooks**. Conversion starts automatically. Setup and implementation code are hidden by default. The supplied v3.1 template is embedded; you do not need to upload it. Each input produces a separately named ZIP, workbook, and review report. Download the ZIP using the button printed for that file.

## Use locally or in Codex

```sh
python -m pip install -r converter/requirements.txt
python converter/convert.py 'your input.xlsx' --output-dir converted
python -m unittest discover -s converter/tests -v
```

Outputs: `your input_converted_v1.03.xlsx`, matching ZIP, and JSON report. Repeating conversion with the same name/version in the same output directory replaces those generated outputs. Keep earlier releases in separate directories.

## What version 1.03 does

- Uses the supplied v3.1 template, retaining all six tabs, styling, merged cells, drawings, print settings, formulas, and supporting files. Writes worksheet XML directly to avoid openpyxl's loss of Excel extensions. Removes Excel dropdown controls while preserving cell colors and other validation.
- Writes sequence data from row 4, preserving all three template heading/instruction rows. Maps source A:C and G:V to the v3.1 sequence fields. Preserves representable source isotypes; maps mini-binders using the supplied example and reports inferred isotypes. Rejects extra-construct/bispecific data rather than silently dropping it.
- Reads Order Details by field labels (including aliases), not fixed row numbers. Only occupied source selection/note cells populate corresponding template fields. Does not insert order defaults. Reads the v4.2 Antibody Settings tab (or Order Details), with labels in A, selections in B, notes in C. Copies contact values from the source, preserving shipping/billing sections.
- Reads dropdown choices from the template itself. Normalized exact matches use template spelling. Closest text matches are flagged for review. An unreliable match leaves the selection blank and retains the original in a note/report. Custom vector names and custom nucleotide sequences are retained.
- Records unmapped fields and duplicate labels in the review report. Review all nonexact selections before submitting an order; similarity does not establish scientific equivalence.

Validation includes synthetic tests for template structure/style preservation, occupied/blank Order Details, sequence placement, ZIP integrity and source-based naming. The supplied Amazon EGFR example converts 258 designs: all Sequence and Order Details values match the supplied expected workbook. Contact values intentionally follow the input because the expected workbook contains different contact details. Analytical SEC is occupied in the input but absent from the expected output; it is recorded as an unmapped request in the report. The workbook has been parsed successfully but has not been visually checked in Microsoft Excel.

The original uploaded notebook is retained under `converter/originals/`; the supplied template is under `converter/templates/`.

Version 1.03 upload controls were tested in Chromium with a mocked Colab kernel bridge: multi-file drag/drop, file picker, per-file error recovery and named ZIP download. Actual Colab browser integration still needs a user check. Optional browser check: `python converter/tests/check_upload_browser.py` requires Playwright and Chromium.

## Unified converter v2.01 — v3.1 fixes

The [unified converter](unified_converter/README.md) now includes a template-preserving v3.1 path. **All 20 v3.1 regression tests pass**, and all 258 example designs plus Order Details match the reference. The [full release report](unified_converter/Twist_Unified_Intake_Converter_v2.01_test_report.md) records 56/59 tests passing and three remaining CSV/EC defects.

[Open unified version 2.01 in Colab](https://colab.research.google.com/github/sweber-maker/SW_tools/blob/main/unified_converter/Twist_Unified_Intake_Converter_v2.01.ipynb). The original v2.0 upload and prior standalone releases are retained.
