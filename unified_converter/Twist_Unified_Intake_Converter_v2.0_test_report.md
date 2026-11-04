# Unified v2.0 baseline test report

Result: **51 tests, 37 passed, 14 failed, 0 errors, 0 skipped**. Tests ran on Python 3.12 with openpyxl 3.1.5 against the unchanged uploaded notebook. Exact Python version, notebook SHA-256, execution time and per-test evidence are in the JSON and text reports. No tests were disabled or marked as expected failures.

## Passed capabilities

- Every EC template flavor: IgG/VHH × Protein A/Nickel/no purification × plate/tube (12 separate tests). Tube routing succeeds with a separated word such as `input tube.xlsx`.
- All four advertised routes: v4.2 → EC/v3.1; EC → v4.2; paired CSV → EC/v4.2/v3.1; legacy XLSX → EC/v4.2/v3.1.
- Heavy/light chain pairing works when CSV rows arrive in reverse order. Representative sequence strings survive each tested route.
- Rejects corrupt or unsupported workbooks, empty input, ambiguous/duplicate/missing CSV partners, inconsistent CSV coordinates, extra constructs, mixed chain counts and mixed purification methods.
- All embedded template ZIP members open and pass ZIP integrity checks. Unknown custom dropdown text is preserved in EC conversion. Wrong output counts are detected.
- A 100-design EC output retains its final design and extends the template validation ranges beyond the original sample rows.
- Batch wrapper continues after an invalid file and reports case-insensitive output collisions. These wrapper tests use a stub converter and redirect the hardcoded `/content` archive path into a temporary directory; actual conversions are covered separately.

## Failed requirements (14 tests)

| Area | Failures | Observed behavior |
| --- | ---: | --- |
| Download naming | 2 | ZIP has a generic name; individual artifacts lack `_converted` and converter release number. |
| Incomplete inputs | 2 | An incomplete CSV record or a named v4.2 design without its first sequence can silently disappear when other rows are valid. |
| Histidine tags | 1 | A six-His tag encoded by alternating CAC/CAT is written as length 3; only CAC is counted. |
| Tube selection | 1 | `input_tube.xlsx` selects a plate template because the filename regular expression treats underscore as a word character. |
| v3.1 template | 2 | Only Sequence and Order Details are generated; template tabs and row-1 instruction content are missing. |
| v3.1 Order Details | 3 | Occupied source scale/cell-line selections are ignored; blank pooling is replaced with a fixed default. |
| v3.1 sequence fields | 3 | Source hIgG2 becomes hIgG1; plate/well fields disappear; a custom Kozak DNA sequence is cleared. |

## Real paired example

Using the previously supplied Amazon EGFR v4.2 input and expected v3.1 output:

- Both EC and v3.1 outputs contain 258 designs.
- All 258 v3.1 design names and their 19-column sequence values match the expected example when aligned by design name. This particular example does not cover the failing hIgG2/custom-Kozak cases.
- Four Order Details input cells differ from the expected output. The output tabs and instruction row do not match the v3.1 template.
- EC reports 310 warnings; v3.1 reports zero despite the Order Details and formatting regressions. Warnings require review before ordering.
- This sample conversion completed in about 2.4 seconds in the current environment, not a performance guarantee.

## Limits and interpretation

Counts and workbook parsing alone do not establish correct scientific selections. Several passing routes still contain the regression failures listed above. Dropdown extension warnings from openpyxl mean some Excel validation features may be discarded; no native Excel visual check was performed. The notebook's live Colab uploader, automatic download and drag/drop behavior remain untested. The imported UI uses native `files.upload()` rather than the previously developed custom drop area.

The prior v1.03 converter remains available and its existing five-test suite still passes. Treat uploaded v2.0 as a baseline for fixes, not a production-ready upgrade.
