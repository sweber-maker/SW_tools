# Changelog

## 2.06

- Add the header-detected, input-only row-1 Sequence intake format (22 v4.2-like columns). Produce EC_upload only.
- Reuse existing signal-DNA handling, mixed-chain EC partitioning, versioned output names and extra-construct rejection/DNA fallback.
- Validate column layout and incomplete named constructs; map diagnostic rows back to the original source.
- Add Incyte as private case 15: 100 paired antibodies, 200 primary sequences and 400 signal-DNA fields preserved in one EC output.
- Pass 17 format tests, 18 signal tests, 10 launcher checks, all 15 private fixtures and the 33-construct Summit reference.


## 2.05

- Resolve source Twist leader/Kozak instruction fields from explicit source DNA definitions or exact known insert-prefix evidence.
- Keep literal custom DNA out of fuzzy dropdown matching; unresolved/non-DNA EC signal values are blank with review messages. Never reverse translate AA inputs.
- Correct the SK example (64 VH leaders) while preserving VL DNA and primary AA sequences; add it as private regression case 14.
- Map the same fixture's 0.5 mg/mL normalization shorthand by concentration.
- Preserve the lightweight START_HERE launcher, source-based versioned outputs and strict extra-construct rejection/fallback.


## 2.04

- Replace the oversized single-code-line notebook with a 3.5 KB root START_HERE launcher and identical versioned notebook.
- Download the frozen runtime package on ▶ from a versioned GitHub tag, verifying its SHA-256 before execution.
- Validate proper notebook cell IDs/schema and display startup errors visibly. Preserve multi-file chooser and drag/drop.
- Conversion logic is byte-identical to 2.03 apart from release identifiers. Ten launcher checks, all 13 private fixtures, and all 33 Summit reference inserts pass.


## 2.03

- Extend the private catalog to 13 real files with Summit: nine three-construct and three two-construct rows. Normal routes reject it; the fallback exports 33 DNA constructs with existing prefixes retained. Converter code/notebook is unchanged; test coverage is extended.

- Add 12 private real-workbook regression cases by filename, hash and independent expected counts. All 12 pass.
- Correct no-shipment cross-field mapping, affirmative/negative sterile-filtration mapping and Micronic container volume matching.
- Normalize existing v3.1 files, repairing invalid input styles while preserving values, service selections and notes.
- Split mixed one/two-chain EC inputs into separate EC_upload workbooks; retain a combined v3.1 output.
- Record 113 synthetic checks (110 passed, three pre-existing CSV/EC failures) and private customer-suite validation.


## 2.02

- Label EC outputs EC_upload and retain source filenames plus release version in every download.
- Scan every v4.2 row and reject normal template conversion for any extra construct, including unnamed/incomplete rows and low-level conversion entry points.
- Export a separate Name / Sequence / Vector Name DNA table with a per-construct assembly audit when all DNA checks succeed.
- Avoid adding existing Kozak/leader prefixes; block protein, ambiguous DNA and uncertain partial/internal matches rather than guessing. Never export a partially failed construct set.
- Distinguish the known empty template formula scaffold from populated or unresolved extra-construct fields.
- Label rejection/failure clearly in Colab and continue other uploads after failures.


## 2.01

- Replace the unified converter's old plain v3.1 workbook generator with a template-preserving engine isolated from EC globals.
- Restore template structure, source-only Order Details, contacts, source isotypes, plate/well positions, and custom Kozak/leader sequences.
- Keep unsupported isotypes in the report and select Other rather than a different IgG subclass; retain custom vector names conservatively.
- Reject named v4.2 designs without their first sequence instead of silently producing inconsistent outputs.
- Embed reviewable engine/UI sources and templates in a self-contained, hidden-code Colab notebook with multiple-file picker and drag/drop.
- Include source names, `_converted`, and version 2.01 in each output; produce one ZIP per upload.
- Add focused and full release evidence: 20 v3.1 checks passed; full release 56/59 passed, with three unchanged CSV/EC defects documented.

## 2.0 uploaded baseline

- Preserve the user-uploaded unified notebook unchanged.
- Record 51-test baseline: 37 passed and 14 failed, plus a paired 258-design comparison.
