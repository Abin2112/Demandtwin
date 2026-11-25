# RACE-Twin for packaged snack choice

## Abstract and problem

Early product evaluation often depends on sparse survey data. DemandTwin proposes to model product choice conditional on explicit alternatives and to evaluate whether aligned purchase evidence and adaptive tasks improve estimation. The initial empirical scope is packaged snacks in Mumbai, with transfer to another city after an independent cohort becomes available.

## Questions and hypotheses

1. Does a purchase-anchored channel model improve calibrated holdout choice probabilities over a hypothetical-choice-only model? The preregistered outcome is paired held-out log loss on observed, eligible choices.
2. Does information-gain design reduce the sample needed to reach a specified share-error target under equal task burden and minimum segment coverage?
3. How much does calibration degrade in a held-out city, and how many local observations restore it?

## Contribution and scope

The proposed contribution is an integrated protocol that tracks evidence type and compares updating and design policies under common evaluation splits. Results from local software benchmarks establish functionality. Claims about empirical improvement require a preregistered protocol and data collection.

Recruit adults under ethics review, record randomized choice sets and outside selections, and collect incentivized or observed purchase opportunities only where the protocol permits them. Fit conditional logit, hierarchical mixed logit and purchase-anchored channel variants. Compare proper scoring rules, uncertainty and subgroup coverage under a predeclared analysis plan. Sampling, hypothetical bias, product assortment and city transfer constrain interpretation.
