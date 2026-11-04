# Changelog

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
