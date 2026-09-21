# Benefit rules: sources and open questions

Captured 2026-09-21 by Bikram Bhattarai.

## Source documents

| Document | URL | SHA-256 |
|---|---|---|
| Medibank OSHC Member Guide (PDF created 16 March 2026, 37 pages) | https://www.medibankoshc.com.au/content/dam/b2c/docs/mpl/Medibank_OSHC_Member_Guide.pdf | 6ca7151567ee2b61f8e6b50340c297d50deb249a013f055ef38f50ed07ec87c7 |
| MBS XML, effective 1 August 2026, released 29 July 2026 | mbsonline.gov.au, August 2026 downloads page, MBS-XML-20260801.XML | c5c04792cbdc7017589b4453aa4506f26b6cfcbfeaee3b0d6c866a8050b06565 |

Printed page numbers match PDF page indices in this edition.

## What each row rests on

- **GP 100 percent, specialist and pathology 85 percent**: p.17, "Out-of-hospital medical services". The 85 percent also covers x-rays and allied health billed with an MBS item number, which have no row yet.
- **Prescriptions abstain**: p.24 defers every amount (co-payment, per-item maximum, annual limit) to the member's Cover Summary, which differs by product. A single row cannot be right for every member.
- **Hospital accommodation abstain**: p.19 table. The benefit depends on whether the hospital is public, Members' Choice private or non-Members' Choice private.
- **Ambulance abstain**: p.25 states when benefits are payable, never an amount.

## Scope condition that applies to every row

p.17 pays these percentages only for services "Included under your cover". Inclusions differ by product and the prototype does not know the member's product. Any figure it shows is conditional on the service being included.

## Open questions for Medibank, via the on-campus contact

1. **Rounding of the 85 percent benefit.** p.17 says "85% of the MBS fee". The MBS XML publishes its own 85 percent amounts, which Medicare rounds: item 104 has fee 103.95 and published 85 percent benefit 88.40, while 85 percent computed is 88.36. Which does Medibank OSHC pay? The prototype currently computes the literal percentage, so its specialist and pathology figures may run a few cents under what Medibank pays.
2. **Cross-reference on p.18** points to p.25 for prescription medicines. They are on p.24.

## Candidate rows not added

Each needs a category the Bill Explainer's schema accepts, so adding them is a minutes decision:
radiology out of hospital (85, p.17), allied health with MBS item (85, p.17), in-hospital medical (100, p.17 and p.19), emergency department facility fee (100 percent of charge, p.18), public hospital outpatient without MBS item (100 percent of charge, p.18).
