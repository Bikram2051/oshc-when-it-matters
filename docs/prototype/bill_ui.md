# Offline Bill Explainer screen

This is a synthetic teaching demonstration, not a
claim assessment or an independently evaluated extraction product.

Run from the repository root in PowerShell:

    $env:OSHC_OFFLINE = "1"
    $env:OSHC_ENABLE_LIVE = "0"
    $env:OSHC_MODEL = "claude-haiku-4-5-20251001"
    python -m streamlit run app/Home.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false

Open the local URL and choose Bill Explainer. Read the text example, enable
the reference comparison, then select Published 100% benefit for item 23.
The charge is AUD 105.00. The example's GP reference difference is AUD 44.95.
The administration fee is unresolved, so the whole-bill comparison stays unknown.
The printed insurer benefit and gap remain Not shown.

Repeat with the PDF and saved AI examples. The saved AI option only replays
the existing cache. Other invented text/PDF inputs use local rules. No live
generation control is exposed. Invalid offline settings block the screen.

Changing the input invalidates old readings, references and downloads. Clear
removes the screen's session values. Synthetic uploads are processed in memory;
the screen does not write bill inputs or create telemetry records. Browser
uploads still reach the local Streamlit process. This is not a real-data intake.

The nine UI regression cases use generated fixtures and mocked reference data.
The separate check script exercises the actual local examples, source and cache:

    python scripts/prototype_check_bill_ui.py

It refuses to overwrite an existing report. Use --out with a new filename for
a later rehearsal. The initial report is docs/prototype/bill_ui_check.json.
Source handling and calculation limits are documented in mbs_reference.md.
Other prototype pages are separate work; this checkpoint implements Bill Explainer.
