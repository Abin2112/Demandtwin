import json

import numpy as np
import pytest

from demandtwin_ml.choice import FEATURES, draws, information_gain, probabilities, rank_designs, scenario, train
from demandtwin_ml.synthetic import candidates, sample


def test_seeded_model_and_roundtrip():
    panel = sample(people=24)
    fitted, report = train(panel)
    again, duplicate = train(sample(people=24))
    assert report == duplicate
    assert again == fitted
    stored = json.loads(json.dumps(fitted))
    result = scenario(stored, candidates()[3], {"balanced": 1, "value": 3}, 1000)
    assert sum(result["choice"]) == pytest.approx(1.0)
    assert result["expected_units"][0] == pytest.approx(result["choice"][1] * 1000)
    assert all(0 <= lo <= hi <= 1 for lo, hi in result["interval_90"])
    assert result["segments"]["value"]["weight"] == 0.75
    assert np.allclose(probabilities(draws(stored, "value"), candidates()[2]).sum(axis=1), 1)
    assert report["train_participants"] + report["test_participants"] == 24
    assert report["metrics"]["conditional_logit_laplace"]["log_loss"] > 0


def test_rank_and_eligibility():
    with pytest.raises(ValueError, match="at least eight"):
        train(sample(people=2))
    options = candidates()
    samples = np.random.default_rng(1).normal(size=(300, len(FEATURES)))
    ranking = rank_designs(samples, options, {}, "adaptive")
    assert ranking[0]["information_gain_nats"] == max(item["information_gain_nats"] for item in ranking)
    assert information_gain(np.zeros((100, len(FEATURES))), options[0]) == pytest.approx(0)
    assert rank_designs(samples, options, {i: 1 for i in range(1, len(options))}, "balanced")[0]["index"] == 0


def test_variable_length_choice_sets_match_direct_likelihood():
    from scipy.optimize import minimize
    from scipy.special import logsumexp
    from demandtwin_ml.choice import Observation, design, fit_mode

    options = candidates()[0]
    rows = [Observation(str(index), "value", options[:1] if index % 2 else options, index % 2)
            for index in range(20)]
    mean = np.zeros(len(FEATURES))
    precision = np.eye(len(FEATURES))
    fitted, covariance = fit_mode(rows, mean, precision)

    def reference(beta):
        return 0.5 * beta @ beta + sum(logsumexp(design(row.alternatives) @ beta)
                                      - design(row.alternatives)[row.chosen] @ beta for row in rows)

    expected = minimize(reference, mean).x
    assert fitted == pytest.approx(expected, abs=1e-4)
    assert np.linalg.eigvalsh(covariance).min() > 0
