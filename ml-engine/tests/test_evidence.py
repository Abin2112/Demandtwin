import pytest

from demandtwin_ml.evidence import Evidence, anchored_preferences, update_individual
from demandtwin_ml.synthetic import sample


def test_channels_require_purchase_overlap():
    rows = sample(people=12)
    hypothetical = [Evidence(row, "hypothetical_choice", "synthetic-hyp", True, True) for row in rows]
    with pytest.raises(ValueError, match="actual-purchase"):
        anchored_preferences(hypothetical)
    purchases = [Evidence(row, "actual_purchase", "synthetic-anchor", True, True) for row in rows]
    model = anchored_preferences(purchases + hypothetical)
    assert set(model["channels"]) == {"actual_purchase", "hypothetical_choice"}
    assert model["coverage"]["hypothetical_choice"]["aligned_participants"] == 12
    individual = update_individual(model["channels"]["hypothetical_choice"], rows[:6])
    assert individual["rows"] == 6


def test_receipts_without_observed_choice_set_are_ineligible():
    row = sample(people=1)[0]
    with pytest.raises(ValueError, match="observed choice set"):
        anchored_preferences([Evidence(row, "actual_purchase", "receipt", False, False)])
