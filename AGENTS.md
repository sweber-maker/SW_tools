# User preferences
- Every downloadable output must include its source upload filename stem plus a simple suffix such as `_converted`.
- Give tools and generated outputs explicit release versions, beginning at 1.01; increment for subsequent changes and maintain a changelog.
- Preserve original uploads. Use Git history for source changes and include the converter version in output filenames and reports.
- Colab tools should use one clean file-selection control with multiple-file upload and automatic processing after selection. Hide implementation/setup code by default; avoid extra upload or conversion steps.
- Always support drag-and-drop as well as the multi-file chooser in Colab upload interfaces.
- Label 12-flavor EC outputs `EC_upload`.
- Any 3rd/4th construct anywhere in a v4.2 workbook rejects all normal template conversions. Offer a separate, audited DNA-only construct table; never reverse translate protein, duplicate existing Kozak/leader sequences, or silently export a partially failed construct set.
