"""Reproduce synthetic design and updating checks; leave human studies pending."""
import argparse
import os
from collections import Counter
from importlib.metadata import version

import numpy as np

from train_all import ARTIFACTS, RESULTS, write_json
from demandtwin_ml.choice import FEATURES, Observation, design, posterior, probabilities, rank_designs
from demandtwin_ml.synthetic import candidates, sample


def sequential():
    options = candidates()
    truth = np.array([0.6, -2.4, 0.7, 0.25, 0.2, -0.3])
    truths = np.array([probabilities(truth[None], task)[0, 1] for task in options])
    prior_mean, prior_covariance = np.zeros(len(FEATURES)), np.eye(len(FEATURES))
    budget, repeats = 24, 8
    summaries = {}
    for strategy in ("random", "balanced", "adaptive"):
        curves = []
        for replicate in range(repeats):
            rng = np.random.default_rng(101 + replicate)
            noise = rng.gumbel(size=(budget, len(options), 3))
            rows, counts = [], Counter()
            mean, covariance = prior_mean, prior_covariance
            steps = []
            for step in range(budget):
                samples = rng.multivariate_normal(mean, covariance, size=256)
                rankings = rank_designs(samples, options, counts, strategy, seed=5000 * replicate + step)
                selected = rankings[0]["index"]
                choice = int(np.argmax(design(options[selected]) @ truth + noise[step, selected]))
                rows.append(Observation("synthetic", "value", options[selected], choice))
                counts[selected] += 1
                update = posterior(prior_mean, prior_covariance, rows)
                mean, covariance = np.asarray(update["mean"]), np.asarray(update["covariance"])
                predicted = np.array([probabilities(mean[None], task)[0, 1] for task in options])
                steps.append({
                    "share_mae": float(np.abs(predicted - truths).mean()),
                    "design_regret_nats": max(item["information_gain_nats"] for item in rankings) - rankings[0]["information_gain_nats"],
                    "selected_information_gain_nats": rankings[0]["information_gain_nats"],
                    "candidate_coverage": len(counts) / len(options),
                })
            curves.append(steps)
        summaries[strategy] = [{
            "observations": step + 1,
            **{key: float(np.mean([curve[step][key] for curve in curves])) for key in curves[0][0]},
        } for step in range(budget)]
    return {"budget": budget, "replicates": repeats, "segment": "synthetic value shopper", "policies": summaries}


def preference_updates():
    options = candidates()
    rng = np.random.default_rng(412)
    baseline_mean = np.zeros(len(FEATURES))
    baseline_cov = np.eye(len(FEATURES))
    truth = np.array([0.6, -2.4, 0.7, 0.25, 0.2, -0.3])
    chronological = [Observation("synthetic", "value", options[i], int(np.argmax(design(options[i]) @ truth + rng.gumbel(size=3))))
                     for i in rng.integers(0, len(options), size=90)]
    initial = posterior(baseline_mean, baseline_cov, chronological[:30])
    methods = ("static", "refit_every_10", "sequential_laplace")
    scores = {}
    for method in methods:
        state = initial
        losses = []
        for i in range(30, len(chronological)):
            row = chronological[i]
            probability = probabilities(np.array(state["mean"])[None], row.alternatives)[0, row.chosen]
            losses.append(float(-np.log(max(1e-12, probability))))
            if method == "sequential_laplace":
                state = posterior(state["mean"], state["covariance"], [row])
            if method == "refit_every_10" and (i + 1) % 10 == 0:
                state = posterior(baseline_mean, baseline_cov, chronological[:i + 1])
        scores[method] = {"prequential_log_loss": float(np.mean(losses)), "test_choices": len(losses)}
    return scores


def checks():
    result = {
        "synthetic": True,
        "experiment_1": "See the two separate benchmark JSON files. The UK repeat and choice outcomes are incompatible.",
        "experiment_2": sequential(),
        "experiment_3": {"status": "pending", "reason": "Individual fidelity requires untouched tasks for human participants."},
        "experiment_4": {"status": "pending", "reason": "Requires randomized price outcomes collected under an approved protocol."},
        "experiment_5": preference_updates(),
        "experiment_6": {"status": "pending", "reason": "Requires independent Mumbai and transfer-city panels."},
        "ablation": {
            "hierarchy": "See conditional_logit_laplace versus empirical_bayes_laplace in sandbox_choice_benchmark.json.",
            "adaptive_design": "Compare all three policies on the same synthetic oracle in experiment_2.",
            "updating": "Compare static, periodic refit and sequential Laplace in experiment_5.",
            "behavioural_calibration": "Pending aligned multiple evidence types with a purchase anchor.",
            "segment_balancing": "Pending multi-segment design policy study.",
        },
    }
    write_json(RESULTS / "choice_experiments.json", result)


def bayesian(tune, n_draws, people):
    if os.name == "nt":
        os.environ.setdefault("PYTENSOR_FLAGS", "cxx=,mode=NUMBA")
    from demandtwin_ml.bayes import fit

    trace, diagnostic = fit(sample(people=people), tune=tune, draws=n_draws)
    for key, value in list(diagnostic.items()):
        if isinstance(value, float) and not np.isfinite(value):
            diagnostic[key] = None
    from pytensor import config
    diagnostic.update(
        synthetic=True, draws_per_chain=n_draws, tune=tune, participants=people, seed=42, chains=4,
        backend=f"PyTensor {config.mode}",
        software_versions={package: version(package) for package in ("pymc", "arviz", "pytensor", "numpy")},
    )
    write_json(RESULTS / "bayes_diagnostics.json", diagnostic)
    target = ARTIFACTS / "choice/bayes_synthetic.nc"
    target.parent.mkdir(parents=True, exist_ok=True)
    trace.to_netcdf(target)
    print(diagnostic)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bayes", action="store_true")
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument("--tune", type=int, default=1000)
    parser.add_argument("--people", type=int, default=30)
    args = parser.parse_args()
    if args.bayes:
        bayesian(args.tune, args.draws, args.people)
    else:
        checks()
