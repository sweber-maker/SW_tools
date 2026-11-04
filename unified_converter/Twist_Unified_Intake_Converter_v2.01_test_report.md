# Unified converter 2.01 — v3.1 repair report

**Focused v3.1: 20 passed, 0 failed. Full release: 56 passed, 3 failed, 0 errors, 0 skipped (59 tests).** The three failures remain visible as ordinary test failures; no assertions were disabled.

## Fixed

All eight v3.1 failures identified in uploaded v2.0 are covered and fixed: missing template tabs, missing instruction row, wrong scale, wrong cell line, invented pooling selection, overwritten isotype, lost plate/well positions, and cleared custom Kozak DNA.

Added coverage checks all four custom sequence columns, unsupported isotype handling, conservative custom vector mapping, placeholder selections, reordered order labels, note-only fields, missing settings, all eight purified scales, source contact sections, the documented mini-binder policy, and cached completion formulas. The style/package test compares every template cell's style reference, layout elements, and unchanged non-worksheet XLSX parts and verifies that list controls are absent.

The new named-design check also prevents a missing first construct sequence from being silently omitted in the unified v4.2 route. Download artifacts now use source filenames, `_converted`, and release version 2.01. The one-cell hidden-code interface retains multi-file picker and drag/drop support for XLSX and CSV inputs.

## Paired 258-design example

| Check | Uploaded 2.0 | Fixed 2.01 |
| --- | ---: | ---: |
| Designs in v3.1 output | 258 | 258 |
| Sequence-cell differences (aligned by name) | 0 | 0 |
| Order Details input-cell differences | 4 | 0 |
| Template tabs match | No | Yes |
| Instruction row preserved | No | Yes |

Source contacts are retained even though the expected example contains different contacts. v3.1 now surfaces 261 review items: the 258 example-confirmed mini-binder mappings, two closest order-choice mappings and the unmapped aSEC request. These are review items, not conversion test failures.

## Unchanged routes and remaining failures

All 12 EC flavor tests and all four input routes pass against the new notebook's embedded engines. However, three existing non-v3-engine defects remain:

- CSV parsing can silently skip an incomplete record among valid pairs, affecting downstream CSV conversions.
- EC His-tag length counts CAC codons but misses CAT codons.
- Filename inference misses an underscore-separated `tube` hint and picks a plate template.

These failures are intentionally retained in the full release report. This repair does not establish that all EC/CSV order selections are correct.

## Evidence and limits

The versioned JSON and text logs provide per-test outcomes and the tested notebook hash. Source fixtures are synthetic; the separately recorded example uses user-provided workbooks outside the repository. The optional Chromium test passed picker input, multi-file drop including CSV, recovery after one invalid file, and source/version-based ZIP naming with the Colab bridge mocked. Live Colab and native Microsoft Excel rendering were not tested.

Run `python unified_converter/run_v2_01_tests.py --v3-only` for the focused check, or omit the flag for the full suite (which returns a failing exit code for the three known defects). The original 2.0 notebook and baseline evidence are retained unchanged.
