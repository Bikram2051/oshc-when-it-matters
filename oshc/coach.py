"""Simple keyness ranking for Journey Coach."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from pathlib import Path

from wordfreq import word_frequency


def keyness_ranked_terms(top_k: int = 30) -> list[tuple[str, float]]:
    """Rank OSHC terms from the 87-record review corpus."""

    data_file = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "gold"
        / "coach_keyness_corpus.csv"
    )

    words = []

    with open(data_file, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            snippet = row["snippet"].lower()

            found_words = re.findall(
                r"[A-Za-z]+(?:['-][A-Za-z]+)*",
                snippet,
            )

            words.extend(found_words)

    counts = Counter(words)
    total_words = len(words)

    # These are not useful glossary terms.
    excluded_words = {
        "medibank",
        "bupa",
        "app",
        "commit",
        "waited",
    }

    results = []

    for word, count in counts.items():
        if count < 2:
            continue

        if len(word) < 3:
            continue

        if word in excluded_words:
            continue

        corpus_frequency = count / total_words
        general_frequency = word_frequency(word, "en")

        if general_frequency == 0:
            general_frequency = 0.000000001

        score = math.log10(
            corpus_frequency / general_frequency
        )

        results.append((word, round(score, 4)))

    results.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return results[:top_k]
