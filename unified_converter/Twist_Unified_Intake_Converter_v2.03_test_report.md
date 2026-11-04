# Unified 2.03 — real-workbook regression results

**Private customer suite: 12/12 files passed. Synthetic release suite: 113 tests, 110 passed, 3 known failures, 0 errors/skips.**

The customer set contains 10 v4.2 inputs and two already-v3.1 inputs. Across the 12 supplied files, 1,330 design rows were retained, including both byte-identical IL2 uploads. No populated third/fourth construct was found. Therefore no simple-list fallback is needed for these real files; the inherited synthetic three/four-construct rejection and DNA-only fallback checks still pass.

## Fixes prompted by the real inputs

- Map source Shipping Container = `No physical shipment` into the dedicated v3.1 no-physical-shipment field, leaving the container blank. Move its associated note to that same target field.
- Map `Yes` for sterile filtration to the template's affirmative choice. Negative selections never become affirmative through fuzzy matching.
- Match Micronic container volume explicitly so a 4 mL request does not become a 1.4 mL choice just because the rest of the description is similar.
- Recognize existing v3.1 inputs and normalize their values onto the supplied template. This repairs the invalid style reference found in the PTPRC input without changing its sequences. Existing service selections and notes remain under their original matching field labels.
- Split mixed one/two-chain v4.2 inputs into separate EC_upload workbooks by chain count; retain one combined v3.1 workbook. The IL2 files each produce 92 one-chain and 94 two-chain EC entries, plus all 186 entries in v3.1.

## Customer-suite assertions

Each source is identified by an expected SHA-256 and explicit expected design count. Tests check:

- Input format and extra-construct scan result, ZIP integrity, output names/version and expected EC partition count.
- Exactly one v3.1 workbook; all source design names, both chain names and complete sequences retained in source order.
- Source plate/well positions and meaningful custom Kozak/leader sequences preserved. Empty dropdown placeholders are treated as unset, not as missing DNA.
- Source contact values, corresponding Order Details choices and notes, including no-shipment and affirmative sterile-filtration semantics. Blank source choices remain blank.
- Existing v3.1 service selections/notes stay associated with the same assay/field labels.
- Every EC partition opens, and the partition union contains each source design and both sequences exactly once.
- All generated v3.1 workbooks open with normal openpyxl loading and use the template's sheets, instruction row and headers. Inherited tests check package/style preservation.

This is data/structure validation, not native Microsoft Excel visual inspection or scientific approval of an order. Existing v3.1 inputs can only be checked against the supplied v3.1 data; their original v4.2 history was not supplied.

## Source-data review items

- Both IL2 inputs are identical and were processed separately as requested. Their required order selections are blank in the source and remain blank in v3.1.
- The Epana request notes describe 14 samples, but only 12 design rows are provided. No missing constructs were fabricated.
- The two Dupilumab source versions have 224 and 225 design rows respectively. Each output follows its own input; they are not treated as duplicates.
- aSEC / other fields without a supported destination are retained as warnings for manual review; a passing conversion does not mean every requested downstream service was transferred automatically. Inspect the warning files before ordering.

The same three shared CSV/EC defects remain visible as ordinary failures in the synthetic suite: incomplete CSV records can be skipped, mixed CAC/CAT His tags are undercounted, and underscore-separated tube filename hints are missed. None of the 12 real-file tests failed, but these general limitations remain.

## Repeatability and privacy

`customer_cases.json` is the versioned list of 12 filenames, hashes, expected formats/counts and EC partitions. No raw workbooks, sequences, contacts or customer note contents are committed. Supply the private fixtures to run:

```sh
python unified_converter/run_customer_tests.py --fixtures-dir /path/to/private/workbooks --output-dir /path/to/private/outputs
python unified_converter/run_v2_03_tests.py
```

A missing or mismatched fixture fails its test; it is not silently skipped or counted as a pass. Byte-identical aliases may use the same matching fixture bytes. The synthetic suite exits nonzero while the three known failures remain.

Picker, drag/drop, per-file recovery and ZIP download naming passed local Chromium checks with the Colab kernel bridge mocked. Live Colab remains a user-browser check. Earlier published notebooks and customer inputs are preserved unchanged.
