from __future__ import annotations

import csv
import hashlib
import re
import urllib.request
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "data" / "rules" / "SOURCES.md"
CORPUS_DIR = ROOT / "corpus"
MANIFEST_FILE = CORPUS_DIR / "MANIFEST.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_sources() -> list[dict[str, str]]:
    text = SOURCES_FILE.read_text(encoding="utf-8")

    sources = []

    for line in text.splitlines():
        if not line.startswith("|") or "http" not in line:
            continue

        columns = [column.strip() for column in line.strip("|").split("|")]

        if len(columns) < 3:
            continue

        document, url, expected_hash = columns[:3]

        # Special handling for the MBS XML source.
        if "MBS-XML-20260801.XML" in document:
            sources.append(
                {
                    "document": document,
                    "url": url,
                    "expected_hash": expected_hash,
                    "local_filename": "MBS-XML-20260801.XML",
                }
            )

        elif url.startswith(("http://", "https://")):
            sources.append(
                {
                    "document": document,
                    "url": url,
                    "expected_hash": expected_hash,
                }
            )

    return sources


def filename_for(document: str, url: str) -> str:
    url_name = Path(url.split("?", 1)[0]).name

    if url_name:
        return url_name

    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", document)

    return cleaned.strip("_") + ".html"


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "OSHC-When-It-Matters-Corpus-Snapshot/1.0"
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def main() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    sources = read_sources()

    if not sources:
        raise RuntimeError(
            f"No approved URLs found in {SOURCES_FILE}"
        )

    capture_date = date.today().isoformat()
    manifest_rows = []

    for source in sources:
        document = source["document"]
        url = source["url"]

        # Use a fixed filename when one is provided.
        filename = source.get("local_filename") or filename_for(
            document,
            url,
        )

        destination = CORPUS_DIR / filename

        print(f"Downloading: {document}")
        print(f"URL: {url}")

        download_file(url, destination)

        actual_hash = sha256_file(destination)

        expected_hash = source["expected_hash"]

        if expected_hash and actual_hash.lower() != expected_hash.lower():
            raise RuntimeError(
                f"SHA-256 mismatch for {filename}\n"
                f"Expected: {expected_hash}\n"
                f"Actual:   {actual_hash}"
            )

        # Set publisher based on the source.
        publisher = "Medibank"

        if "mbsonline" in url.lower():
            publisher = "MBS Online"

        title = document

        manifest_rows.append(
            {
                "URL": url,
                "Title": title,
                "Publisher": publisher,
                "Capture Date": capture_date,
                "SHA-256": actual_hash,
            }
        )

        print(f"Saved: {destination}")
        print(f"SHA-256: {actual_hash}")
        print()

    with MANIFEST_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "URL",
                "Title",
                "Publisher",
                "Capture Date",
                "SHA-256",
            ],
        )

        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Manifest created: {MANIFEST_FILE}")
    print(
        f"Captured {len(manifest_rows)} source(s) "
        f"on {capture_date}"
    )


if __name__ == "__main__":
    main()