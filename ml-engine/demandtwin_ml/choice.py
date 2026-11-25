"""Conditional choice models with an explicit outside option and Laplace uncertainty."""
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax

FEATURES = ("concept", "price_per_30_inr", "size_per_50_g", "spicy", "resealable", "premium")
SEGMENTS = ("value", "balanced", "premium")
FEATURE_VERSION = "snacks-v1"


def features(product):
    return np.array([
        1.0,
        product["price"] / 30,
        product["grams"] / 50,
        float(product.get("flavour") == "spicy"),
        float(product.get("packaging") == "resealable"),
        float(product.get("positioning") == "premium"),
    ])


def design(products):
    return np.vstack([np.zeros(len(FEATURES)), *(features(product) for product in products)])


@dataclass(frozen=True)
class Observation:
    participant: str
    segment: str
    alternatives: list
    chosen: int


def fit_mode(observations, prior, precision):
    """Find the Gaussian-prior posterior mode and its local covariance."""
    if not observations:
        return np.asarray(prior).copy(), np.linalg.inv(precision)
    matrices = [design(item.alternatives) for item in observations]
    width = max(len(matrix) for matrix in matrices)
    features_by_task = np.zeros((len(matrices), width, len(FEATURES)))
    available = np.zeros((len(matrices), width), dtype=bool)
    for index, matrix in enumerate(matrices):
        features_by_task[index, :len(matrix)] = matrix
        available[index, :len(matrix)] = True
    chosen_features = np.array([matrix[item.chosen] for matrix, item in zip(matrices, observations, strict=True)])

    def prediction(beta):
        utility = features_by_task @ beta
        return np.where(available, utility, -np.inf)

    def objective(beta):
        diff = beta - prior
        utility = prediction(beta)
        loss = 0.5 * diff @ precision @ diff + np.sum(logsumexp(utility, axis=1) - chosen_features @ beta)
        probability = softmax(utility, axis=1)
        expected = np.einsum("nk,nkd->nd", probability, features_by_task)
        gradient = precision @ diff + (expected - chosen_features).sum(axis=0)
        return loss, gradient

    result = minimize(objective, prior, method="L-BFGS-B", jac=True, options={"ftol": 1e-11})
    if not result.success or not np.isfinite(result.x).all():
        raise ValueError("Choice model optimization did not converge")
    probability = softmax(prediction(result.x), axis=1)
    expected = np.einsum("nk,nkd->nd", probability, features_by_task)
    centered = features_by_task - expected[:, None, :]
    hessian = precision + np.einsum("nki,nk,nkj->ij", centered, probability, centered)
    return result.x, np.linalg.inv(hessian)


def posterior(mean, covariance, rows):
    mode, cov = fit_mode(rows, np.asarray(mean), np.linalg.inv(covariance))
    return {"mean": mode.tolist(), "covariance": cov.tolist(), "rows": len(rows)}


def fit_artifact(rows, hierarchical=True):
    prior = np.zeros(len(FEATURES))
    base = posterior(prior, np.eye(len(prior)) * 9, rows)
    segments = {}
    if hierarchical:
        for segment in SEGMENTS:
            group = [row for row in rows if row.segment == segment]
            segments[segment] = posterior(base["mean"], np.eye(len(prior)) * 0.75, group)
    matrix = np.vstack([design(row.alternatives)[1:] for row in rows])
    return {
        "feature_version": FEATURE_VERSION,
        "features": FEATURES,
        "global": base,
        "segments": segments,
        "support_min": matrix.min(axis=0).tolist(),
        "support_max": matrix.max(axis=0).tolist(),
        "method": "empirical_bayes_laplace" if hierarchical else "conditional_logit_laplace",
    }


def parameter(artifact, segment):
    group = artifact["segments"].get(segment)
    return group if group and group["rows"] else artifact["global"]


def draws(artifact, segment, seed=21, size=512):
    group = parameter(artifact, segment)
    return np.random.default_rng(seed).multivariate_normal(group["mean"], group["covariance"], size)


def probabilities(samples, alternatives):
    return softmax(samples @ design(alternatives).T, axis=1)


def metrics(probabilities_by_row, chosen):
    selected = np.array([p[y] for p, y in zip(probabilities_by_row, chosen, strict=True)])
    brier = [sum((p - np.eye(len(p))[y]) ** 2) for p, y in zip(probabilities_by_row, chosen, strict=True)]
    confidence = np.array([p.max() for p in probabilities_by_row])
    correct = np.array([p.argmax() == y for p, y in zip(probabilities_by_row, chosen, strict=True)])
    calibration = []
    for low in np.linspace(0, 0.9, 10):
        mask = (confidence >= low) & (confidence < low + 0.1 + (1e-8 if low > 0.89 else 0))
        if mask.any():
            calibration.append({"confidence": float(confidence[mask].mean()), "accuracy": float(correct[mask].mean()), "n": int(mask.sum())})
    return {
        "rows": len(chosen), "log_loss": float(-np.log(selected.clip(1e-12)).mean()),
        "brier": float(np.mean(brier)), "accuracy": float(correct.mean()), "calibration": calibration,
    }


def train(rows, seed=42):
    people = sorted({row.participant for row in rows})
    if len(people) < 8 or len(rows) < 24 or len({row.chosen == 0 for row in rows}) < 2:
        raise ValueError("Training requires at least eight participants, 24 choices, and observed product and no-purchase selections")
    rng = np.random.default_rng(seed)
    held_out = set(rng.permutation(people)[:max(2, len(people) // 5)])
    training = [row for row in rows if row.participant not in held_out]
    test = [row for row in rows if row.participant in held_out]
    scores = {}
    for hierarchical in (False, True):
        artifact = fit_artifact(training, hierarchical)
        posterior_samples = {segment: draws(artifact, segment, seed) for segment in SEGMENTS}
        predictions = [probabilities(posterior_samples[row.segment], row.alternatives).mean(axis=0) for row in test]
        score = metrics(predictions, [row.chosen for row in test])
        score["segments"] = {
            segment: metrics(
                [prediction for prediction, row in zip(predictions, test, strict=True) if row.segment == segment],
                [row.chosen for row in test if row.segment == segment],
            )
            for segment in SEGMENTS if any(row.segment == segment for row in test)
        }
        scores[artifact["method"]] = score
    return fit_artifact(rows), {
        "seed": seed, "split": "grouped by participant; repeated designs may appear on both sides",
        "train_rows": len(training), "test_rows": len(test), "train_participants": len(people) - len(held_out),
        "test_participants": len(held_out), "metrics": scores, "serving_fit": "all eligible observations",
    }


def information_gain(samples, alternatives):
    p = probabilities(samples, alternatives).clip(1e-15)
    marginal = p.mean(axis=0)
    return max(0.0, float(np.mean(np.sum(p * (np.log(p) - np.log(marginal)), axis=1))))


def rank_designs(samples, candidates, completed, strategy: Literal["adaptive", "balanced", "random"], seed=42):
    rng = np.random.default_rng(seed)
    ranked = []
    for idx, alternatives in enumerate(candidates):
        eig = information_gain(samples, alternatives)
        burden = len(alternatives)
        priorities = {"adaptive": eig / burden, "balanced": -completed.get(idx, 0), "random": float(rng.uniform())}
        ranked.append({
            "index": idx, "information_gain_nats": eig, "alternatives": burden,
            "completed": completed.get(idx, 0), "score": priorities[strategy],
        })
    return sorted(ranked, key=lambda item: (item["score"], -item["completed"]), reverse=True)


def scenario(artifact, products, weights, opportunities):
    weights = {segment: weight / sum(weights.values()) for segment, weight in weights.items()}
    low, high = np.array(artifact["support_min"]), np.array(artifact["support_max"])
    x = design(products)[1:]
    outside = np.any((x < low - 1e-9) | (x > high + 1e-9), axis=0)
    warnings = [f"Outside training support: {name}" for name, flag in zip(FEATURES, outside, strict=True) if flag]
    segments = {}
    aggregate = 0
    own_derivative = 0
    for index, (segment, weight) in enumerate(sorted(weights.items())):
        if segment in artifact["segments"] and not artifact["segments"][segment]["rows"]:
            warnings.append(f"No observations for segment {segment}; using pooled preferences")
        beta = draws(artifact, segment, seed=21 + index)
        p = probabilities(beta, products)
        segments[segment] = {
            "weight": weight,
            "choice": p.mean(axis=0).tolist(),
            "price_coefficient": float(beta[:, 1].mean() / 30),
            "utility_contributions": (x[0] * beta.mean(axis=0)).tolist(),
            "choice_interval_90": np.quantile(p, [0.05, 0.95], axis=0).T.tolist(),
        }
        aggregate += weight * p
        own_derivative += weight * np.mean(beta[:, 1] / 30 * p[:, 1] * (1 - p[:, 1]))
    means = aggregate.mean(axis=0)
    intervals = np.quantile(aggregate, [0.05, 0.95], axis=0).T
    return {
        "choice": means.tolist(), "interval_90": intervals.tolist(),
        "expected_units": (means[1:] * opportunities).tolist(),
        "units_interval_90": (intervals[1:] * opportunities).tolist(),
        "elasticity": float(own_derivative * products[0]["price"] / means[1]) if means[1] > 1e-8 else None,
        "segments": segments, "warnings": warnings, "abstain": bool(warnings),
        "interpretation": "Conditional scenario per stated opportunity. Intervals capture approximate parameter uncertainty.",
    }
