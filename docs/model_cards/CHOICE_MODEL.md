# Choice model card

The deployed model is an empirical Bayes segment-level conditional logit with a Laplace approximation. Its baseline uses pooled coefficients. Each candidate shares six features, including the concept intercept and scaled price and size. No purchase has utility zero. Segment-specific coefficients shrink toward the pooled estimate. The API fits each run from scratch on its study data, records grouped-participant holdout scores, and refits the serving artifact on all eligible responses.

The sandbox holdout contains 108 choices from 18 of 90 generated participants. Pooled log loss was 0.9209, versus 0.8715 for the segment fit. The tasks can recur across participants and splits. A separate task-holdout evaluation is required to claim generalization to unseen tasks.

Intervals quantify conditional parameter uncertainty under the approximation. Coefficient contributions are additive on the utility scale. The model checks marginal support and flags extrapolations. Marginal checks can miss unsupported feature combinations. Segment weights are analyst inputs and the simulator normalizes them. The model does not estimate frequency, reach, availability, revenue, or causal effects.

The offline PyMC model represents individual effects and segment heterogeneity explicitly. The four-chain [synthetic diagnostic run](../../research/results/bayes_diagnostics.json) passed the project's diagnostic gate. The purchase-anchored channel research module needs aligned actual-choice and auxiliary evidence, with explicit observed choice sets. UK receipts lack those choice sets.
