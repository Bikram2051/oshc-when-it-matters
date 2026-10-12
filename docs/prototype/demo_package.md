# NextBest offline demonstration

University prototype. This package reproduces the four-screen demo,
not the full research repository or its independent evaluation suite.

Use the exact Python version, operating system and architecture recorded in
package_manifest.json. The initial package targets Windows AMD64, Python 3.13.9.
Python itself is not included. Runtime dependencies are included as wheels, with
exact versions and SHA-256 hashes. No dependency download is needed at setup.

Extract the ZIP into a new folder. In PowerShell, open the extracted NextBest-demo
folder and run:

    .\Start_Demo.ps1

Python must be available as python. Alternatively supply -Python followed by the
full path to the required python.exe. The launcher creates a sibling virtual
environment, installs the included wheels, verifies files and versions, and
starts http://127.0.0.1:8501. Stop an existing server first. Stop with Ctrl+C.

Use the three saved synthetic bill examples. The saved AI reading replays an
earlier response; new paid extraction is disabled. Missing benefits and gaps
remain unknown. MBS comparisons are educational references, not claim decisions.
The Navigator uses the frozen guide. The Dashboard shows historical checks with
their scope. These checks do not establish independent accuracy or learning impact.

No API key, private spending ledger, original virtual environment, Git metadata
or held-out invoices are included. The Medibank guide and MBS snapshot retain
their source attribution in corpus/MANIFEST.csv. This is a local demonstration
package, not an insurer-approved service or a public deployment.

The archive SHA-256 is supplied separately. File hashes detect changes; they are
not digital signatures. Keep the original ZIP and checksum together.
