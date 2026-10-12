# Bill input and rules baseline

Implemented 2026-10-01. This is a local prototype component.

- `read_text(text)` and `read_pdf(bytes_or_path)` return `BillText`.
- `extract(text_or_billtext)` returns the existing frozen `ExtractionResult`.
- PDF limits: 10 MiB, 20 pages, 100,000 extracted characters. Words are grouped
  by vertical position and horizontal gaps. This is a layout heuristic.
- Password-protected, damaged, oversized or textless-page PDFs return warnings
  and no extracted text. No OCR is attempted and no PDF is sent to an API.
- A PDF can mix selectable text with unreadable images on the same page. Review
  extracted rows against the original; this reader cannot prove completeness.
- The rules baseline recognises tables separated by pipes, tabs or at least
  two spaces. A description/service column and an explicit charge/fee column
  are required. Missing or malformed values remain unknown; zero stays zero.
- Benefits require an explicit paid-insurer-benefit label. `Paid`, `Amount paid`,
  `Benefit` and `Estimated benefit` are intentionally not interpreted as benefits paid.
- Service dates accept ISO YYYY-MM-DD and Australian DD/MM/YYYY or DD-MM-YYYY.
- Row and total consistency checks use Decimal arithmetic. Conflicting printed
  totals remain unknown; a printed total differing from row sums is retained
  with a warning, never silently replaced by the sum.
- No gap, benefit or missing total is inferred. No MBS matching or coverage
  decision happens in this stage. Unknown values are not treated as zero.
- Unsupported cases include scans, unlabelled/vertical tables, wrapped rows,
  foreign-currency bills, credit notes and ambiguous unit-fee/quantity layouts.
  These require review or a later supported extraction path.
- The demo text/PDF and unit-test inputs are synthetic development fixtures.
  They are not independent gold labels, held-out cases or evidence of real-bill accuracy.
- The frozen schemas, arithmetic module, seminar rules and held-out files are unchanged.

Technical references:
- https://pymupdf.readthedocs.io/en/latest/recipes-text.html
- https://pymupdf.readthedocs.io/en/latest/document.html
