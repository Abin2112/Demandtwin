"""Optional full hierarchical Bayesian fit for offline choice research."""
import numpy as np

from .choice import SEGMENTS, design


def fit(rows, seed=42, tune=1000, draws=1000):
    import pymc as pm
    import pytensor.tensor as pt

    people = sorted({row.participant for row in rows})
    person_index = {person: i for i, person in enumerate(people)}
    group = {row.participant: SEGMENTS.index(row.segment) for row in rows}
    matrices = [design(row.alternatives) for row in rows]
    width = max(len(matrix) for matrix in matrices)
    n_features = matrices[0].shape[-1]
    x = np.zeros((len(rows), width, n_features))
    mask = np.zeros((len(rows), width), dtype=bool)
    for idx, matrix in enumerate(matrices):
        x[idx, :len(matrix)] = matrix
        mask[idx, :len(matrix)] = True
    indices = [person_index[row.participant] for row in rows]
    chosen = np.asarray([row.chosen for row in rows])
    with pm.Model() as model:
        population = pm.Normal("population", 0, 1.5, shape=n_features)
        segment_scale = pm.HalfNormal("segment_scale", 0.7, shape=n_features)
        individual_scale = pm.HalfNormal("individual_scale", 0.7, shape=n_features)
        segment_offset = pm.Normal("segment_offset", 0, 1, shape=(len(SEGMENTS), n_features))
        segment = pm.Deterministic("segment", population + segment_scale * segment_offset)
        individual_offset = pm.Normal("individual_offset", 0, 1, shape=(len(people), n_features))
        individual = segment[[group[p] for p in people]] + individual_scale * individual_offset
        utility = pt.sum(x * individual[indices, None, :], axis=-1)
        pm.Categorical("chosen", logit_p=pt.where(mask, utility, -np.inf), observed=chosen)
        trace = pm.sample(tune=tune, draws=draws, chains=4, cores=1, target_accept=0.93, random_seed=seed)
        pm.sample_posterior_predictive(trace, extend_inferencedata=True, random_seed=seed)
    return trace, diagnostics(trace)


def diagnostics(trace):
    import arviz as az

    monitored = ["population", "segment", "segment_scale", "individual_scale", "individual_offset"]
    summary = az.summary(trace, var_names=monitored, round_to="none")
    rhat = float(np.max(summary["r_hat"].to_numpy()))
    ess = float(np.min(summary[["ess_bulk", "ess_tail"]].to_numpy()))
    divergences = int(trace.sample_stats.diverging.sum())
    replicated = (trace.posterior_predictive.chosen == 0).mean(dim="chosen_dim_0").values.ravel()
    return {
        "rhat_max": rhat, "ess_min": ess, "divergences": divergences,
        "reliable": bool(np.isfinite(rhat) and np.isfinite(ess) and rhat <= 1.01 and ess >= 400 and divergences == 0),
        "observed_no_purchase_rate": float((trace.observed_data.chosen == 0).mean()),
        "replicated_no_purchase_interval_90": np.quantile(replicated, [0.05, 0.95]).tolist(),
    }
