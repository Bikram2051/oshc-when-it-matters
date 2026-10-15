"""Local text-category baselines trained explicitly on supplied frozen labels.

Input: nonempty text and C1..C6/S training labels. Output: a frozen-schema Code.
Never use this module for a safety decision. No source data, model downloads,
API calls, synthetic labels, or pretrained classifier are silently substituted.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from oshc.schemas import Code

LADDER = ("majority", "tfidf_logreg", "embed_knn", "llm_zeroshot")
SEED = 20261014


@dataclass
class LocalClassifier:
    step: str
    majority: Code
    estimator: Any = None
    constant_fallback: bool = False

    def predict(self, text: str) -> Code:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Classification requires nonempty text.")
        if self.estimator is None:
            return self.majority
        return Code(self.estimator.predict([text])[0])


def fit_classifier(
    texts: Iterable[str], labels: Iterable[Code | str], *, step: str = "tfidf_logreg"
) -> LocalClassifier:
    """Fit one baseline using only this training set, with fixed hyperparameters.

    A single-class training fold has an explicitly flagged constant fallback.
    Neither the vectorizer nor the label distribution sees validation text.
    """
    if step not in ("majority", "tfidf_logreg"):
        raise NotImplementedError(f"Classifier step {step!r} has not been evaluated.")
    samples = list(texts)
    categories = [Code(label) for label in labels]
    if not samples or len(samples) != len(categories):
        raise ValueError("Training texts and labels must have the same nonzero length.")
    if any(not isinstance(text, str) or not text.strip() for text in samples):
        raise ValueError("Every training text must be nonempty.")
    counts = Counter(categories)
    majority = max(Code, key=lambda code: counts[code])
    model = LocalClassifier(step=step, majority=majority)
    if step == "majority":
        return model
    if len(counts) == 1:
        model.constant_fallback = True
        return model

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    model.estimator = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
        ("logreg", LogisticRegression(
            C=1.0, class_weight="balanced", max_iter=2000, random_state=SEED,
        )),
    ])
    model.estimator.fit(samples, [code.value for code in categories])
    return model


_installed: dict[str, LocalClassifier] = {}


def install_classifier(model: LocalClassifier) -> None:
    """Opt in to an explicitly trained local analytics model for this process."""
    _installed[model.step] = model


def predict(text: str, *, step: str = "tfidf_logreg") -> Code:
    """Route text for analytics only, after an explicit local model installation.

    The original public signature and Code schema remain unchanged. The safety
    guardrail remains independent and must run before any conversational action.
    """
    if step not in ("majority", "tfidf_logreg"):
        raise NotImplementedError(f"Classifier step {step!r} has not been evaluated.")
    if step not in _installed:
        raise RuntimeError("Train and install a local classifier before requesting predictions.")
    return _installed[step].predict(text)
