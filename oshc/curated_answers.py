"""Authored general explanations, each sentence bound to a specific guide column."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class GroundedSentence:
    text: str
    page: int
    column: str
    anchor: str


@dataclass(frozen=True)
class CuratedCard:
    ident: str
    title: str
    sentences: tuple[GroundedSentence, ...]


CURATED_CARDS = {
    "claims": CuratedCard("claims", "Making a claim", (
        GroundedSentence("For most medical claims, use your Medibank OSHC online member account or OSHC app and attach the relevant invoices and receipts.", 29, "left", "A claim can be submitted online for most medical services using an OMS account"),
        GroundedSentence("Claims over $1,000 and inpatient hospital claims use the separate online submission route listed in the passage below.", 29, "left", "Claims over $1000"),
        GroundedSentence("Keep copies of your documents. Claims must be submitted within two years of the service or purchase date.", 29, "right", "Claims must be submitted within two years of the date of service or the date the item was purchased."),
    )),
    "waiting_periods": CuratedCard("waiting_periods", "Understanding waiting periods", (
        GroundedSentence("A waiting period is time you must serve before benefits become available. Services received during a waiting period generally do not qualify for benefits.", 21, "right", "A Waiting period is a set amount of time each member must wait before they can receive Benefits under their cover."),
        GroundedSentence("The rules depend on the service and your circumstances. Check the waiting-period section and your Cover Summary; this answer does not decide whether you have served a waiting period.", 21, "right", "Waiting periods are outlined below:"),
    )),
    "membership_card": CuratedCard("membership_card", "Your membership card", (
        GroundedSentence("Your membership card arrives with your welcome pack or shortly afterwards. Use it for visits, hospital admission, claims and membership enquiries; photo ID may also be requested.", 8, "left", "You will also receive a membership card, either with your welcome pack or shortly after."),
        GroundedSentence("Keep the card safe and tell Medibank immediately if it is lost or stolen.", 8, "left", "Make sure you keep your card safe and advise us immediately if it is lost or stolen."),
    )),
    "mbs": CuratedCard("mbs", "What the MBS means", (
        GroundedSentence("The Medicare Benefits Schedule (MBS) lists services and government-set fees used to calculate Medicare benefits. An MBS fee is a reference amount; it is not necessarily the price a provider charges.", 17, "left", "Doctors and providers are not restricted to charging the MBS fee"),
        GroundedSentence("For included outpatient services, the guide describes benefits based on the MBS fee. The service must meet the policy conditions; an item number alone does not confirm your payment.", 17, "right", "If a service you receive as an Outpatient is listed in the MBS and Included under your cover"),
    )),
    "gap": CuratedCard("gap", "Why there can be a gap", (
        GroundedSentence("A gap is the difference between the provider's charge and the benefit paid. If the provider charges more than the benefit, the remaining amount is an out-of-pocket expense.", 17, "right", "difference between the Benefit we pay and the provider's charge."),
        GroundedSentence("A printed bill charge or an MBS reference cannot, by itself, confirm your final gap. Check the benefit assessment and the applicable policy conditions.", 17, "right", "If a service you receive as an Outpatient is listed in the MBS and Included under your cover"),
    )),
    "direct_billing": CuratedCard("direct_billing", "How direct billing works", (
        GroundedSentence("A Direct Billing provider has an agreement to send the bill directly to Medibank. This can reduce or remove the upfront payment, but a gap may still apply.", 28, "right", "has an agreement with Medibank to send the bill directly to us."),
        GroundedSentence("Before booking, ask whether the provider still participates and whether any out-of-pocket charge applies. Take your membership card and photo ID.", 28, "right", "Remember to take your membership card and photo identification."),
    )),
    "prescriptions": CuratedCard("prescriptions", "Prescription medicine costs", (
        GroundedSentence("OSHC can help with eligible prescribed medicines. You pay a set contribution before benefits, and an amount above the benefit may remain out of pocket.", 24, "left", "You will need to pay a set contribution amount"),
        GroundedSentence("Your Cover Summary sets the contribution, per-item maximum and annual limits. Medicines available without a prescription are excluded under the rules shown below.", 24, "right", "For medicines available without a prescription"),
    )),
    "exclusions": CuratedCard("exclusions", "Understanding exclusions", (
        GroundedSentence("Some services and circumstances do not qualify for benefits. The guide lists exclusions, including services excluded by your cover, services during applicable waiting periods, and claims submitted too late.", 27, "left", "Benefit exclusions."),
        GroundedSentence("Read the full exclusion list with your Cover Summary. This general explanation cannot decide whether a particular service or claim is covered.", 28, "left", "Benefit exclusions."),
    )),
}


def match_intent(question: str) -> str | None:
    patterns = (
        ("direct_billing", r"\bdirect\s+billing\b"),
        ("waiting_periods", r"\bwaiting\s+periods?\b"),
        ("membership_card", r"\bmembership\s+cards?\b"),
        ("claims", r"\b(?:claim|claims|claiming)\b"),
        ("gap", r"\b(?:gap|out.of.pocket)\b"),
        ("mbs", r"\b(?:mbs|medicare benefits schedule)\b"),
        ("prescriptions", r"\b(?:prescription|prescriptions|medicines|pharmacy)\b"),
        ("exclusions", r"\b(?:exclusion|exclusions|excluded)\b"),
    )
    matched = [ident for ident, pattern in patterns if re.search(pattern, question)]
    # Multi-topic questions fall back to passages; one canned answer must not
    # pretend to answer a second request.
    return matched[0] if len(matched) == 1 else None
