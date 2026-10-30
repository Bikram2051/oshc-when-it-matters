# NextBest offline demonstration

University prototype. This package reproduces the six-page demo,
not the full research repository or its independent evaluation suite.

Home introduces the tools; Journey Coach provides three sourced lessons;
Navigator opens the guide; Bill Explainer reads synthetic examples; Ask NextBest
accepts general questions; and Project dashboard presents saved project evidence.

Use the exact Python version, operating system and architecture recorded in
package_manifest.json. This package targets Windows AMD64, CPython 3.13.9, with
Streamlit 1.64.0 and 44 pinned runtime distributions.
Python itself is not included. Runtime dependencies are included as wheels, with
exact versions and SHA-256 hashes. No dependency download is needed at setup.

Extract the ZIP into a new folder. In PowerShell, open the extracted NextBest-demo
folder and run:

    .\Start_Demo.ps1

Python must be available as python. Alternatively supply -Python followed by the
full path to the required python.exe. The launcher creates a sibling virtual
environment, installs the included wheels, verifies files and versions, and
starts http://127.0.0.1:8501. Stop an existing server first. Stop with Ctrl+C.

Use the saved GP examples or the dated paid receipt. The saved AI reading replays an
earlier response; new paid extraction is disabled. Missing benefits and gaps
remain unknown. MBS comparisons are educational references, not claim decisions.
The Navigator uses the frozen guide. Ask NextBest checks every submitted question
before source loading or retrieval. It shows curated general answers with verified
source passages, or fixed refusal/clarification messages. It does not generate novel policy answers, assess symptoms
or decide personal benefits. Emergency and refused questions cannot retrieve a
follow-up passage. Follow-ups must name their topic; previous circumstances are
not reused as context. Chat stays in bounded session memory and Clear chat removes
it. Avoid personal details; rejected question text is withheld from the transcript.

Project dashboard has Overview, Results, Safety and Evidence & sources tabs. It
distinguishes saved engineering checks, aggregate coding agreement, historical
retrieval results and a separate seminar guardrail experiment. Separately authored
automated probes of the final chat recorded 24/24 required refusals, 6/6 emergency
escalations and 6/20 false refusals. Independently authored source labels found the
correct guide column in the top five for 23/25 guide questions. These are automated
assessments, with small selected sets and known scope limits. They do not establish unseen-document
accuracy or learning impact. The agreement export contains aggregate statistics
only; individual coding decisions and coder names are excluded. Final development
chat scores, automated-label classifier scores and the new synthetic bill
evaluation are included. The low narrative-invoice score is an explicit limitation.

Bill names, identifiers, provider identities and original descriptions are removed
from retained results and downloads. The selected upload temporarily lives in
browser/server RAM; Clear removes app state. No bill files are written to disk,
sent to an external model, or included in this package. Use synthetic data only.

No API key, private spending ledger, original virtual environment, Git metadata
raw review records, probe files or held-out invoices are included. The Medibank guide and MBS snapshot retain
their source attribution in corpus/MANIFEST.csv. This is a local demonstration
package, not an insurer-approved service or a public deployment.

The archive SHA-256 is supplied separately. File hashes detect changes; they are
not digital signatures. Keep the original ZIP and checksum together.
