"""Keep exact and punctuation-only duplicate snippets in the same fold."""
from eval.classification import assign_groups


def test_groups_join_threads_and_normalised_duplicate_text():
    rows = [
        {"thread": "one", "text": "A sufficiently long original text"},
        {"thread": "one", "text": "Different wording from one thread"},
        {"thread": "two", "text": "a sufficiently long original text!!!"},
        {"thread": "three", "text": "Unrelated receipt upload error"},
    ]
    groups = assign_groups(rows)
    assert groups[0] == groups[1] == groups[2]
    assert groups[0] != groups[3]
