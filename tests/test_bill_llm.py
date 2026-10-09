'''Engineering cases written for development. Model responses are mocked, not evaluation results.'''

import json
from copy import deepcopy
from unittest.mock import Mock

import pytest

import oshc.llm as adapter
from oshc.billexplainer import extract_llm as module
from oshc.billexplainer.read import BillText
from oshc.llm import CacheMiss, OutputValidationError, ProviderError
from oshc.llm_budget import BudgetError


TABLE = 'Item | Description | Charge\n23 | Short consultation | $90.00\nTotal charged: $90.00'
ROW = {'start_line': 2, 'end_line': 2, 'header_line': 1,
       'raw_description': 'Short consultation', 'item_number': '23', 'charged': '$90.00'}
BLOCK = 'Description: Short consultation\nItem: 23\nCharge: $90.00\nAmount paid: $90.00'


@pytest.fixture(autouse=True)
def forbid_provider(monkeypatch):
    monkeypatch.setattr(adapter, '_client', Mock(side_effect=AssertionError('Unexpected provider access')))
    monkeypatch.setenv('OSHC_OFFLINE', '1')
    monkeypatch.setenv('OSHC_ENABLE_LIVE', '0')


def run(monkeypatch, text=TABLE, row=None, metadata=None):
    payload = {'rows': [deepcopy(ROW if row is None else row)], **(metadata or {})}
    draft = module.BillEvidence.model_validate(payload)
    mocked = Mock(return_value=draft)
    monkeypatch.setattr(module, 'complete_json', mocked)
    return module.extract(text), mocked


def test_table_values_are_verified_and_missing_values_stay_unknown(monkeypatch):
    result, mocked = run(monkeypatch, metadata={'total_charged': {'line': 3, 'text': '$90.00'}})
    item = result.line_items[0]
    assert (item.item_number, item.charged, item.benefit_paid, item.gap) == ('23', 90, None, None)
    assert (item.matched, item.mbs_descriptor, item.mbs_match_score) == (False, None, None)
    assert (result.total_charged, result.total_benefit, result.total_gap) == (90, None, None)
    assert result.extractor == 'llm'
    args, kwargs = mocked.call_args
    assert json.loads(args[0])['bill_lines'][1] == {'line': 2, 'text': TABLE.splitlines()[1]}
    assert args[1] is module.BillEvidence and kwargs['repair'] is False
    assert kwargs['max_tokens'] == 3072


def test_labelled_block_does_not_treat_patient_payment_as_benefit(monkeypatch):
    row = dict(ROW, start_line=1, end_line=4, header_line=None, benefit_paid='$90.00')
    result, _ = run(monkeypatch, BLOCK, row)
    assert result.line_items[0].charged == 90
    assert result.line_items[0].benefit_paid is None
    assert any('benefit_paid has no matching' in text for text in result.warnings)


@pytest.mark.parametrize('field,value', [('charged', '$9.00'), ('item_number', '24'),
                                        ('gap', '$90.00'), ('benefit_paid', '$90.00')],
                         ids=['invented-charge', 'wrong-item', 'inferred-gap', 'inferred-benefit'])
def test_invented_or_mislabelled_field_is_unknown(monkeypatch, field, value):
    result, _ = run(monkeypatch, row=dict(ROW, **{field: value}))
    assert getattr(result.line_items[0], field) is None
    assert any('no matching labelled evidence' in text for text in result.warnings)


@pytest.mark.parametrize('label', ['Paid', 'Amount paid', 'Benefit', 'Estimated benefit'])
def test_ambiguous_or_estimated_payment_columns_are_not_benefits(monkeypatch, label):
    text = f'Item | Description | Charge | {label}\n23 | Short consultation | $90.00 | $40.00'
    result, _ = run(monkeypatch, text, dict(ROW, benefit_paid='$40.00'))
    assert result.line_items[0].benefit_paid is None


def test_explicit_zero_benefit_is_preserved(monkeypatch):
    text = 'Item | Description | Charge | Benefit paid | Gap\n23 | Short consultation | $90.00 | $0.00 | $90.00'
    result, _ = run(monkeypatch, text, dict(ROW, benefit_paid='$0.00', gap='$90.00'))
    assert (result.line_items[0].benefit_paid, result.line_items[0].gap) == (0, 90)


@pytest.mark.parametrize('printed,proposed', [('-$90.00', '$90.00'), ('$90.001', '$90.00'),
                                           ('$90.00', '90.00'), ('$1,200.00', '$200.00')],
                         ids=['minus-sign', 'precision', 'currency-stripped', 'numeric-substring'])
def test_partial_money_quotes_are_rejected(monkeypatch, printed, proposed):
    result, _ = run(monkeypatch, TABLE.replace('$90.00', printed), dict(ROW, charged=proposed))
    assert result.line_items[0].charged is None


def test_description_rewrite_rejects_row(monkeypatch):
    result, _ = run(monkeypatch, row=dict(ROW, raw_description='Invented procedure'))
    assert not result.line_items


def test_wrong_table_column_cannot_borrow_a_number(monkeypatch):
    text = 'Item | Description | Charge | Benefit paid\n23 | Short consultation | $90.00 | $40.00'
    result, _ = run(monkeypatch, text, dict(ROW, charged='$40.00'))
    assert result.line_items[0].charged is None


def test_row_cannot_borrow_charge_from_another_service(monkeypatch):
    text = TABLE.replace('Total charged: $90.00', '36 | Long consultation | $150.00')
    result, _ = run(monkeypatch, text, dict(ROW, charged='$150.00'))
    assert result.line_items[0].charged is None


def test_overlapping_or_duplicate_model_rows_are_rejected(monkeypatch):
    draft = module.BillEvidence.model_validate({'rows': [ROW, ROW]})
    monkeypatch.setattr(module, 'complete_json', Mock(return_value=draft))
    assert not module.extract(TABLE).line_items


def test_legitimate_identical_rows_at_different_lines_are_kept(monkeypatch):
    text = '\n'.join(TABLE.splitlines()[:2] + [TABLE.splitlines()[1]])
    draft = module.BillEvidence.model_validate({'rows': [ROW, dict(ROW, start_line=3, end_line=3)]})
    monkeypatch.setattr(module, 'complete_json', Mock(return_value=draft))
    assert len(module.extract(text).line_items) == 2


@pytest.mark.parametrize('row', [dict(ROW, start_line=9, end_line=9), dict(ROW, end_line=1),
                               dict(ROW, header_line=2)], ids=['outside-source', 'reversed', 'self-header'])
def test_invalid_source_positions_reject_row(monkeypatch, row):
    assert not run(monkeypatch, row=row)[0].line_items


def test_incomplete_labelled_block_rejects_row(monkeypatch):
    row = dict(ROW, start_line=1, end_line=3, header_line=None)
    assert not run(monkeypatch, BLOCK, row)[0].line_items


def test_table_cannot_reuse_an_old_header(monkeypatch):
    text = '\n'.join([TABLE.splitlines()[0], 'Item | Description | Benefit paid | Charge',
                      '23 | Short consultation | $90.00 | $40.00'])
    row = dict(ROW, start_line=3, end_line=3)
    assert not run(monkeypatch, text, row)[0].line_items


def test_quantity_unit_price_is_not_a_line_charge(monkeypatch):
    text = 'Item | Description | Quantity | Fee\n23 | Short consultation | 2 | $90.00'
    assert not run(monkeypatch, text)[0].line_items


def test_table_summary_is_not_a_service(monkeypatch):
    text = 'Item | Description | Charge\n- | Total | $90.00'
    row = dict(ROW, raw_description='Total', item_number=None)
    assert not run(monkeypatch, text, row)[0].line_items


def test_complete_negative_amount_is_still_rejected(monkeypatch):
    result, _ = run(monkeypatch, TABLE.replace('$90.00', '-$90.00'), dict(ROW, charged='-$90.00'))
    assert result.line_items[0].charged is None


def test_conflicting_totals_are_not_cherry_picked(monkeypatch):
    text = TABLE + '\nTotal charged: $100.00'
    result, _ = run(monkeypatch, text, metadata={'total_charged': {'line': 3, 'text': '$90.00'}})
    assert result.total_charged is None
    assert any('conflicting source values' in text for text in result.warnings)


def test_unprinted_totals_are_never_summed(monkeypatch):
    result, _ = run(monkeypatch, TABLE.split('\nTotal')[0], metadata={'total_charged': {'line': 2, 'text': '$90.00'}})
    assert result.total_charged is None


def test_metadata_requires_complete_matching_labelled_evidence(monkeypatch):
    text = TABLE + '\nProvider: Demonstration Clinic\nService date: 01/09/2026'
    metadata = {'provider': {'line': 4, 'text': 'Demonstration Clinic'},
                'service_date': {'line': 5, 'text': '01/09/2026'}}
    result, _ = run(monkeypatch, text, metadata=metadata)
    assert (result.provider, result.service_date) == ('Demonstration Clinic', '2026-09-01')
    metadata['provider']['text'] = 'Different Clinic'
    assert run(monkeypatch, text, metadata=metadata)[0].provider is None


@pytest.mark.parametrize('source', ['', '\x00', 'x' * (module.MAX_INPUT_BYTES + 1),
                                  '\n'.join(['a'] * (module.MAX_LINES + 1)), 'USD 90.00', 'Currency: US$',
                                  BillText('anything', 'image')],
                         ids=['empty', 'binary', 'oversized', 'too-many-lines', 'foreign-currency', 'foreign-symbol', 'image'])
def test_unsupported_input_never_requests_model(monkeypatch, source):
    mocked = Mock(side_effect=AssertionError('Unexpected model request'))
    monkeypatch.setattr(module, 'complete_json', mocked)
    result = module.extract(source)
    assert not result.line_items and result.warnings
    mocked.assert_not_called()


@pytest.mark.parametrize('error', [CacheMiss, ProviderError, OutputValidationError, BudgetError])
def test_model_failure_returns_no_bill_values_or_fallback(monkeypatch, error):
    mocked = Mock(side_effect=error('private diagnostic detail'))
    monkeypatch.setattr(module, 'complete_json', mocked)
    result = module.extract(TABLE)
    assert not result.line_items and result.total_charged is None
    assert any(error.__name__ in text for text in result.warnings)
    assert all('private diagnostic detail' not in text for text in result.warnings)
    mocked.assert_called_once()


def test_offline_cache_miss_is_handled_through_real_adapter(monkeypatch, tmp_path):
    monkeypatch.setattr(adapter, 'CACHE_DIR', tmp_path)
    result = module.extract(TABLE)
    assert not result.line_items
    assert any('CacheMiss' in text for text in result.warnings)


def test_pdf_provenance_and_reader_warning_survive(monkeypatch):
    result, _ = run(monkeypatch, BillText(TABLE, 'pdf_text', ('Review PDF layout.',), 1))
    assert result.source_kind == 'pdf_text' and 'Review PDF layout.' in result.warnings
