# Unified 2.02 — extra constructs and DNA fallback

**105 tests: 102 passed, 3 failed, 0 errors, 0 skipped.** All new extra-construct, DNA assembly, fallback, status and naming checks passed. All 20 inherited v3.1 regression checks and the 12 EC template variants passed. The three existing failures remain ordinary failing tests, not skipped or marked expected failures.

## Standard conversion rejection

Tests reject three/fourth construct data through the unified processor, direct v3.1 function, EC converter, legacy routing helper and normalized-chain-to-v4.2 entry point. The scan examines every source row before conversion, including unnamed rows and rows lacking a first construct sequence. An isolated fourth construct or a third construct name without DNA is sufficient to reject normal conversion.

Tests distinguish menu placeholders and the bundled blank formula scaffold from actual extra-construct fields. Unknown unresolved formulas are not assumed empty; cached formula DNA is detected. A two-part ratio does not by itself imply three constructs, while a declared missing third/fourth construct produces a validation failure.

## Fallback workbook and audit

Tests verify a three-column **Name / Sequence / Vector Name** table for three and four constructs and for a mixed workbook containing two- and three-construct rows. The whole workbook uses the fallback; no normal v3.1 or EC_upload workbook is emitted. An audit JSON links each construct to its source row and records assembly actions and warnings.

One invalid construct blocks the entire DNA table; the ZIP still contains rejection/failure details. Duplicate names are retained and flagged. Missing component/vector data receives review warnings. Formula-looking names are stored as literal Excel text. Failed uploads do not prevent other uploads from completing.

## Assembly checks

- Existing full Kozak + leader prefixes are retained, including inputs with a preceding cloning overhang.
- Missing Kozak, missing leader and missing whole prefixes are added in the correct order without duplicating an existing component.
- A leader field already containing Kozak does not cause a duplicate Kozak.
- Lowercase and whitespace normalize without changing DNA bases. Short coincidental overlaps are not trimmed.
- Pre-existing repeated full prefixes are retained and flagged, not silently repaired.
- Reversed components, uncertain partial prefixes and isolated internal Kozak matches require manual review.
- An incidental internal Kozak motif does not prevent adding a missing 5-prime Kozak before an already present leader.
- Protein, ambiguous bases, RNA, unresolved formulas and missing insert DNA fail validation. There is no reverse translation or codon guessing.
- The UI marks fallback vs failure explicitly and still offers downloadable reports.

These checks validate literal unambiguous DNA and assembly operations, not reading frame, orientation, leader function or biological suitability. A protein made entirely of letters A/C/G/T cannot be distinguished from DNA by alphabet alone. Missing separate Kozak/leader sequences are reported as unverifiable rather than invented.

## Existing 258-design reference

The real two-construct v4.2 example still produces 258 v3.1 records with **zero sequence-cell differences and zero Order Details input differences**, matching template tabs and instructions. EC output is now labeled **EC_upload**. No new real three/four-construct workbooks were provided; fallback validation uses synthetic fixtures.

## Remaining known failures and limits

1. The shared CSV parser can silently skip an incomplete record among valid pairs, affecting downstream output completeness.
2. The shared EC engine undercounts His tags encoded by mixed CAC/CAT codons.
3. The shared EC engine misses underscore-separated tube hints in filenames.

These were not changed by this release. The full test command therefore returns exit status 1. Review warnings before submitting orders.

Local Chromium tests passed the multi-file picker, drag/drop including CSV, per-file error recovery and source/version-based ZIP download naming with a mocked Colab kernel bridge. Live Colab and native Microsoft Excel rendering were not tested.

Run `python unified_converter/run_v2_02_tests.py` for reproducible outcomes; the JSON/text reports record the exact notebook hash and dependency versions. The original upload and earlier release notebooks remain unchanged.
