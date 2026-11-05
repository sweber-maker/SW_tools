# 2.05 — actual DNA in EC signal fields

The SK workbook exposed an EC conversion bug: all 64 VH leader values contained an instruction string which also exists as a valid template dropdown option. The old categorical matcher accepted it verbatim. The source Leader Setting is explicitly `Twist Sequence`, and the source workbook defines the corresponding literal 51-base leader DNA at `Dropdown Lists!B18`.

Version 2.05 resolves that setting from the source definition before EC/v3.1 conversion. All 64 VH leader fields now contain the source-defined DNA; all 64 literal VL leaders remain unchanged. Both primary antibody sequence columns contain supplied amino-acid sequences, which are preserved. This is not reverse translation and does not prepend anything to those sequences.

## Resolution policy

- Literal signal DNA is preserved rather than fuzzy-matched to DNA or instruction choices. EC outputs normalize only case/whitespace, not nucleotide bases.
- A missing/instruction value can use a unique source-defined DNA choice when the source explicitly selects `Twist Sequence`.
- Otherwise a known DNA candidate must match the exact insert start, optionally after the separately provided Kozak. Internal matches are insufficient.
- If neither source setting nor exact DNA evidence establishes the sequence, the instruction is cleared and a manual-review item is emitted. A protein-only custom signal is not reverse translated or written into an EC DNA field.
- VH and VL leader/Kozak fields use the same safeguards. Primary DNA-or-AA insert sequences are unchanged.
- The source workbook bytes are never overwritten. Corrections are made only in a temporary in-memory copy; source cell coordinates and resolution reasons appear in the output reports.

The v3.1 shorthand `0.5 mg/mL` selection in this same fixture is also mapped by concentration to `0.5 mg/mL Normalization` rather than relying on a low text-similarity score.

## Evidence

- 18 focused signal tests pass, including all 12 EC template variants as subtests, literal one-base custom DNA preservation, both chain roles, explicit/inferred defaults, ambiguous/missing definitions, unresolved instructions, protein-only signals, a paired-CSV route, v3.1 propagation and normalization shorthand.
- All 10 small-launcher checks pass; the notebook remains about 3.5 KB.
- All 14 private customer-file cases pass. Case 14 checks every corrected VH leader against the source-defined DNA, literal VL leader preservation, and unchanged names/primary sequence records. All EC signal columns are checked for literal DNA or blank values, never dropdown prose or protein.
- All 33 Summit reference inserts continue to match exactly; extra-construct rejection/fallback rules are unchanged.

The three prior shared CSV/EC defects remain documented (incomplete CSV records, mixed CAC/CAT His-tag counting, underscore-separated tube hints). This release does not claim to fix them. Native Excel rendering and the user's live Colab session are not available for verification; startup and the upload bridge are tested locally.

Run:

```sh
python -m unittest discover -s unified_converter/signal_tests -v
python -m unittest discover -s unified_converter/launcher_tests -v
python unified_converter/run_customer_tests.py --notebook START_HERE.ipynb --fixtures-dir /private/workbooks --output-dir /private/outputs
```

Raw customer fixtures and corrected workbooks remain private. GitHub stores the metadata catalogue, hashes, sanitized results and runtime code only. The original SK input and prior published releases are preserved.
