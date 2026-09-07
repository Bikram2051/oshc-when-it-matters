"""Synthetic invoice generator. ReportLab to PDF, PyMuPDF to PNG.

Emits gold JSON alongside every document, so the ground truth comes from the
generator and never from a human reading the output.

ROLE SEPARATION, enforced by process not by code:
  - Minhaj owns this file. Bikram does not read it and does not review its diffs.
  - Two of four layout families are frozen as held-out. Their parameters live in
    data/heldout/ which is gitignored until evaluation day.
  - Aayush reviews this file, because Bikram writes the extractor it is scored
    against.

Owner: Md Minhaj Rahman. Reviewer: Aayush Khade.
"""
from __future__ import annotations

FAMILIES = ("gp_simple", "pathology_multiline", "specialist_gap", "hospital_mixed")
HELD_OUT = ("specialist_gap", "hospital_mixed")  # frozen before extraction code exists


def main() -> None:
    raise NotImplementedError("Week 7 gate: v1 with two families frozen held-out.")


if __name__ == "__main__":
    main()
