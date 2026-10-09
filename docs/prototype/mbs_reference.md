# MBS reference comparisons

Constructed engineering checks. These are not
independent invoice evaluation results or evidence of real-world accuracy.

`oshc.billexplainer.mbs_reference.load_snapshot()` reads only the approved August
2026 XML after checking its SHA-256. It performs no download or database write.
Duplicate items or fields fail the load. The resulting lookup is immutable.

`compare_bill(extracted, snapshot, bases)` returns separate reference comparisons.
Supply one explicit basis per line: `ScheduleFee`, `Benefit85`, `Benefit100`, or
`None`. Neither the broad MBS category nor the description selects a percentage.
Only an exact, canonical printed item number can produce a comparison. An unknown
number never falls back to description matching. No item eligibility is inferred.

Amounts use Decimal and the published XML fields. For item 104 the published
Benefit85 is AUD 88.40, not the AUD 88.36 obtained by multiplying 103.95 by 0.85.
The comparison retains the source amount, caps the amount used at the charge,
then subtracts it from that charge. This is illustrative arithmetic, not an OSHC
benefit, claim decision or actual out-of-pocket amount.

The development window is 2026-08-01 through 2026-09-28, inclusive. Item, fee,
benefit and time-limited listing dates are checked where applicable. This is a
conservative engineering restriction for a frozen snapshot, not proof that no
intervening revision occurred. Newer dates require a reviewed source update.
Derived fees, unclear dates and missing amounts abstain. The source dates do not
establish the student's policy eligibility, referral conditions or coverage.

Input ExtractionResult and its printed benefits/gaps are not modified. A total
difference appears only if every line resolves and line charges equal the
printed total. An omitted or unresolved row prevents an aggregate.

The frozen arithmetic.py and benefit_rules.csv are unchanged. Their generic
percent_of_mbs path is not suitable for published Benefit85 amounts. Prototype
integration must use this new reference module for MBS comparisons; policy
application remains a separate step requiring verified policy context.

Sources: corpus/MANIFEST.csv, docs/prototype/mbs_source_check.json, and
https://www.mbsonline.gov.au/internet/mbsonline/publishing.nsf/Content/FAQ-XML_Help

The local verification report is docs/prototype/mbs_reference_check.json.
