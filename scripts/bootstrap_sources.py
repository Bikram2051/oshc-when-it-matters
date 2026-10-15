"""Restore the two pinned public sources without changing the frozen manifest.

Run explicitly during setup, never from a student question or an upload handler.
Only official HTTPS endpoints are used. A download is published only after its
SHA-256 matches the pinned source, and existing files are never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
BLOCK_BYTES = 1024 * 1024
ALLOWED_HOSTS = frozenset({"www.medibankoshc.com.au", "www.mbsonline.gov.au"})


class SourceBootstrapError(ValueError):
    """A source cannot be safely restored or verified."""


@dataclass(frozen=True)
class Source:
    filename: str
    manifest_url: str
    download_url: str
    sha256: str


GUIDE_URL = (
    "https://www.medibankoshc.com.au/content/dam/b2c/docs/mpl/"
    "Medibank_OSHC_Member_Guide.pdf"
)
MBS_PAGE = (
    "https://www.mbsonline.gov.au/internet/mbsonline/publishing.nsf/"
    "Content/Downloads-20260801"
)
# Direct XML link on the frozen release's official download page; not a ZIP.
MBS_DOWNLOAD = (
    "https://www.mbsonline.gov.au/internet/mbsonline/publishing.nsf/"
    "650f3eec0dfb990fca25692100069854/81efb2067580a870ca258e28007f588c/"
    "%24FILE/MBS-XML-20260801.XML"
)
SOURCES = (
    Source("Medibank_OSHC_Member_Guide.pdf", GUIDE_URL, GUIDE_URL,
           "6ca7151567ee2b61f8e6b50340c297d50deb249a013f055ef38f50ed07ec87c7"),
    Source("MBS-XML-20260801.XML", MBS_PAGE, MBS_DOWNLOAD,
           "c5c04792cbdc7017589b4453aa4506f26b6cfcbfeaee3b0d6c866a8050b06565"),
)


def validate_url(url: str) -> None:
    """Reject transport downgrades and redirects outside the observed publishers."""
    parsed = urllib.parse.urlsplit(url)
    try:
        allowed = (parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
                   and parsed.port in (None, 443) and parsed.username is None
                   and parsed.password is None and not parsed.fragment)
    except ValueError:
        allowed = False
    if not allowed:
        raise SourceBootstrapError("The source URL or redirect is not an approved HTTPS endpoint.")


class OfficialRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def load_sources(root: Path = ROOT, *, guide_only: bool = False) -> tuple[Source, ...]:
    """Require agreement between the tracked manifest and application source pins."""
    try:
        with (Path(root) / "corpus/MANIFEST.csv").open(
                encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error) as error:
        raise SourceBootstrapError("Cannot read corpus/MANIFEST.csv. Restore the tracked manifest.") from error
    selected = SOURCES[:1] if guide_only else SOURCES
    for source in selected:
        matches = [row for row in rows if row.get("URL", "").strip() == source.manifest_url]
        if (len(matches) != 1
                or matches[0].get("SHA-256", "").strip().lower() != source.sha256):
            raise SourceBootstrapError(
                f"The manifest does not match the pinned source: {source.filename}. "
                "Restore the tracked manifest; do not replace a pin with a newer document."
            )
        validate_url(source.download_url)
    return selected


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as handle:
        while block := handle.read(BLOCK_BYTES):
            count += len(block)
            if count > MAX_DOWNLOAD_BYTES:
                raise SourceBootstrapError("The source exceeds the 200 MiB size limit.")
            digest.update(block)
    return digest.hexdigest()


def _existing(destination: Path, source: Source) -> bool:
    if not destination.exists() and not destination.is_symlink():
        return False
    if destination.is_symlink() or not destination.is_file() or _digest(destination) != source.sha256:
        raise SourceBootstrapError(
            f"Existing {source.filename} differs from the pin; it was not overwritten. "
            "Move that file aside explicitly, then restore the matching frozen snapshot."
        )
    return True


def _open(url: str):
    validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "NextBest-Source-Bootstrap/1.0"})
    return urllib.request.build_opener(OfficialRedirectHandler()).open(request, timeout=45)


def _publish(temporary: Path, destination: Path) -> None:
    if os.name == "nt":
        # Windows rename fails if destination exists; unlike POSIX rename, it
        # cannot overwrite a file that appeared while the download was running.
        os.rename(temporary, destination)
    else:
        # A same-directory hard link has the same no-overwrite property on POSIX.
        os.link(temporary, destination)


def ensure_source(source: Source, corpus: Path, *, check: bool = False) -> str:
    """Stream a missing file to a private temporary path, verify, then publish it."""
    corpus = Path(corpus)
    destination = corpus / source.filename
    if _existing(destination, source):
        return "verified"
    guidance = (
        f"Restore the frozen {source.filename} into corpus/ with SHA-256 {source.sha256}, "
        "then run python scripts/bootstrap_sources.py --check. "
        "Do not substitute a newer source or change the recorded hash."
    )
    if check:
        raise SourceBootstrapError(f"Missing {source.filename}. {guidance}")
    corpus.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{source.filename}.", suffix=".download",
                                         dir=corpus, delete=False) as handle:
            temporary = Path(handle.name)
            digest = hashlib.sha256()
            size = 0
            with _open(source.download_url) as response:
                validate_url(response.geturl())
                declared = response.headers.get("Content-Length")
                if declared is not None and (not declared.isdecimal()
                                             or int(declared) > MAX_DOWNLOAD_BYTES):
                    raise SourceBootstrapError("Invalid or oversized source Content-Length.")
                while block := response.read(BLOCK_BYTES):
                    size += len(block)
                    if size > MAX_DOWNLOAD_BYTES:
                        raise SourceBootstrapError("The source exceeds the 200 MiB size limit.")
                    digest.update(block)
                    handle.write(block)
            handle.flush()
            os.fsync(handle.fileno())
        if not size or digest.hexdigest() != source.sha256:
            raise SourceBootstrapError(f"Downloaded {source.filename} failed its pinned SHA-256 check.")
        # Publish complete verified bytes atomically, without replacing a file
        # that another process may have created during the download.
        try:
            _publish(temporary, destination)
        except FileExistsError:
            _existing(destination, source)
            return "verified"
        return "downloaded and verified"
    except (OSError, ValueError) as error:
        raise SourceBootstrapError(f"Could not restore {source.filename}. {guidance} ({type(error).__name__})") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guide-only", action="store_true", help="Restore only the source needed by chat and Navigator.")
    parser.add_argument("--check", action="store_true", help="Verify existing snapshots without any network access.")
    args = parser.parse_args(argv)
    try:
        for source in load_sources(guide_only=args.guide_only):
            print(f"{source.filename}: {ensure_source(source, ROOT / 'corpus', check=args.check)}")
    except SourceBootstrapError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
