# Antigen Lookup · version 1.01

Research assistant for manufacturer product fields, purchase quantities and pack offers. Original app and quantity-reference workbook are preserved unchanged in `originals/`.

## Browser use

Open `Antigen_Lookup_v1.01.ipynb` in Google Colab and run its single setup cell once. Enter a direct manufacturer product URL or drop/select multiple CSV/XLSX files. Batch lookup starts automatically. Colab accesses the public internet without a local script or tunnel, but some vendors block data-center IPs, require cookies, or render their products in JavaScript. This notebook cannot bypass those restrictions. The notebook's clone URL requires the repository to be accessible to the Colab user and this release to be pushed first. A private repository needs a separately authorized checkout; no tokens are embedded in the notebook.

For a permanent app link, deploy `antigen_lookup/app.py` using Streamlit Community Cloud and the adjacent `requirements.txt`. Deployment is not part of this release and has not been performed. Uploaded data and URLs are processed on the runtime/hosting provider you choose.

## Local development

```sh
cd /workspace/SW_tools
python3 -m venv /workspace/.venvs/sw-tools
/workspace/.venvs/sw-tools/bin/python -m pip install -r antigen_lookup/requirements.txt
/workspace/.venvs/sw-tools/bin/python -m streamlit run antigen_lookup/app.py --server.address 0.0.0.0 --server.headless true
/workspace/.venvs/sw-tools/bin/python -m unittest discover -s antigen_lookup/tests -v
```

## Quantity rules

Source: `originals/SPR (Carterra) & BLI (Octet) & ELISA_Reagent Amt_Reference.xlsx`, sheet `Octet & Carterra Menu (4-26-24)`.

- BLI: cell H40; 4,000 µL at 250 nM; capacity 96 antibodies per batch.
- SPR: cell H15; 2,000 µL at 1,000 nM; capacity 372 antibodies per batch (not 384).
- These source quantities already cover **two runs**. Do not double them again.
- Required µg = assembly MW in kDa × concentration in nM × volume in µL / 1,000,000 × batch count.
- Batch count is ceiling(antibodies / capacity). Full allowance is used for partial batches; this is a conservative app policy, not a workbook interpolation formula.
- Multiply monomer MW by 2 for a confirmed dimer/Fc dimer or 3 for a confirmed trimer. If the supplied MW already describes the assembled oligomer, do not multiply again. Unknown stoichiometry requires confirmation.
- Purchase target rounds **up** to a multiple of 100 µg; an exact multiple remains unchanged. Epitope binning is disabled.

Example: 19.4 kDa Human IL-20 monomer, 96 BLI antibodies → 19.4 µg required → 100 µg purchase target. 372 SPR antibodies → 38.8 µg → 100 µg. 384 SPR antibodies require 2 batches → 77.6 µg → 100 µg.

## Fields, stock and pricing

Use an exact product URL and preferably catalog number. Supported manufacturer domains: ACROBiosystems, Sino Biological, GenScript. Explicit two-column HTML tables/definition lists are matched for tags, storage, formulation, MW, oligomer, extinction coefficient, affinity, and homology. Product title/JSON-LD can supply name; catalog mismatch withholds product data. Values remain **review candidates**, with excerpts and source/retrieval time in the workbook. Conflicting values stay blank. `Vendor-Supplied` is the intake supplier category; manufacturer is recorded separately.

Price/stock must be attached to a matching structured product offer. Only offers naming one explicit pack size, a numeric price and currency receive total-price calculations. Same-size pack options show packs needed and total purchased mass; mixed-size pack optimization is not implemented. Compare only offers with the same currency and market. Availability is a timestamped site assertion, not a reservation. Unknown stock, request-a-quote prices, shipping/tax, regional restrictions, and insufficient pack information must be checked manually.

This is not yet a complete manufacturer research engine: no catalog search adapters, PDF/CoA extraction, free-text scientific interpretation, binding-partner disambiguation, or JavaScript browser automation. Do not equate canonical sequence MW with commercial construct MW or treat homology/affinity without its stated context as universally applicable. The uploaded example values are not used as verified vendor evidence. Actual vendor pages and real Colab browser execution remain unverified in this environment because vendor access is currently denied.

## Batch format and outputs

Required column: `URL`. Optional columns: `Catalog`, `MW_kDa`, `Oligomer` (1/2/3), `MW_basis` (`monomer` or `assembly`), `Format` (`BLI` or `SPR`), `Antibodies`. Row values override sidebar/widget defaults. Missing MW or oligomer leaves calculations blank. Catalog identifiers should be stored as text.

Each uploaded `filename.csv`/`.xlsx` produces `filename_lookup_v1.01.xlsx`; original uploads remain unchanged. Single lookups produce `antigen_lookup_v1.01.xlsx` (there is no uploaded filename). Reports contain intake fields, source evidence, offers, purchase options, calculation inputs, warnings, manufacturer text and version metadata. Generated files with identical names overwrite earlier downloads according to your browser/runtime behavior; retain releases separately.

Tests use synthetic HTML and offers; they demonstrate calculation/extraction behavior, not live vendor compatibility.
