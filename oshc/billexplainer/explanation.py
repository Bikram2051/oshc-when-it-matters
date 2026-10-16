"""Deterministic arithmetic explanations. No policy or clinical inference."""
from decimal import Decimal
from oshc.schemas import ExtractionResult
from oshc.billexplainer.extract_document import ReceiptFacts


def aud(value):
    return f"AUD {Decimal(str(value)):,.2f}"


def explain(result: ExtractionResult, receipt: ReceiptFacts) -> tuple[str, ...]:
    messages = []
    charges = [item.charged for item in result.line_items]
    if charges and all(value is not None for value in charges):
        total = sum((Decimal(str(value)) for value in charges), Decimal(0))
        messages.append(f"The {len(charges)} service lines add up to {aud(total)}.")
        if result.total_charged is not None:
            messages.append("That matches the printed total charge." if total == Decimal(str(result.total_charged))
                            else "That does not match the printed total. Check the original bill before using these numbers.")
    if receipt.amount_settled is not None:
        messages.append(f"The receipt records {aud(receipt.amount_settled)} settled with the provider. This field does not identify an insurer benefit.")
    if receipt.balance_remaining is not None:
        messages.append(f"The printed balance remaining is {aud(receipt.balance_remaining)}. This is the provider's account balance, not your final insurance gap.")
    if result.total_benefit is None:
        messages.append("No total insurer benefit is explicitly shown. A receipt marked paid cannot tell us how much an insurer paid or will reimburse.")
    else:
        messages.append(f"The document explicitly labels {aud(result.total_benefit)} as the insurer benefit. This is a document reading, not a new claim assessment.")
    if result.total_gap is None:
        messages.append("The final insurance gap remains unknown. Do not subtract a published MBS fee and call the result your actual gap.")
    if result.service_date is None:
        messages.append("A single service date could not be established; check each service row in the original document.")
    return tuple(messages)
