# Changelog

## 1.03
- Add an explicit drag-and-drop upload area with a native multiple-file picker.
- Convert automatically on drop or selection and provide browser ZIP downloads.
- Retain hidden startup code and source-based output naming.


## 1.02
- Replace the multi-cell Colab workflow with one hidden-code startup cell and a single multiple-file picker.
- Automatically convert selected files and show one download button per result.
- Retain release 1.01 notebook for traceability; workbook conversion rules remain unchanged.


## 1.01
- Initial repository release based on uploaded Fast Batch Fixed notebook.
- Preserve original v3.1 workbook package and formatting, remove dropdown controls.
- Replace fixed Order Details defaults with occupied-source-only label mapping.
- Match template option spelling and report uncertain mappings.
- Source filename + `_converted_v1.01` for every generated workbook, ZIP and report.
- Add self-contained Colab notebook, command-line tool and regression tests.

Original upload had no explicit converter release number; v4.2 and v3.1 refer to form formats, not tool release versions.
- Validated all 258 designs and Order Details against supplied paired examples; preserve source contact data and report unsupported aSEC request.
