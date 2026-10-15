"""Offline analytics classifier contracts; these are never safety decisions."""
import pytest

from oshc.classifier import fit_classifier, install_classifier, predict
from oshc.schemas import Code


def test_majority_learns_training_distribution_and_breaks_ties_stably():
    model = fit_classifier(["one", "two", "three"], [Code.S, Code.C2, Code.S], step="majority")
    assert model.predict("unseen text") == Code.S
    tied = fit_classifier(["one", "two"], [Code.S, Code.C1], step="majority")
    assert tied.predict("unseen text") == Code.C1


def test_tfidf_fits_only_supplied_training_examples():
    model = fit_classifier(
        ["claim receipt upload", "submit claim receipt", "doctor clinic booking", "book doctor clinic"],
        [Code.C4, Code.C4, Code.C3, Code.C3],
    )
    assert model.predict("claim receipt") == Code.C4
    assert model.predict("doctor clinic") == Code.C3
    assert "secret" not in model.estimator.named_steps["tfidf"].vocabulary_
    install_classifier(model)
    assert predict("doctor clinic") == Code.C3


def test_single_class_training_is_explicit_constant_fallback():
    model = fit_classifier(["receipt"], [Code.C4])
    assert model.constant_fallback
    assert model.predict("anything") == Code.C4


def test_validation_and_unsupported_steps():
    with pytest.raises(ValueError):
        fit_classifier([], [])
    with pytest.raises(ValueError):
        fit_classifier(["one"], ["unknown"])
    with pytest.raises(ValueError):
        fit_classifier(["one", "two"], [Code.C1])
    with pytest.raises(NotImplementedError):
        fit_classifier(["one"], [Code.C1], step="llm_zeroshot")


def test_empty_text_is_not_silently_classified():
    model = fit_classifier(["one"], [Code.C1], step="majority")
    with pytest.raises(ValueError):
        model.predict(" ")
