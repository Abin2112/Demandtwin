# Engineering experiment report

## External transaction benchmark

The evaluation uses 1,375 training customers and 479 disjoint test customers, with August and October 2011 snapshots. The test positive rate was 0.340. See [full metrics](uk_retail_benchmark.json), [SHAP summary](uk_retail_shap.json) and [EDA](eda/online_retail.json).

| Model | ROC-AUC | Log loss | Brier |
| --- | ---: | ---: | ---: |
| Logistic regression | 0.6550 | 0.6075 | 0.2074 |
| Random forest | 0.6530 | 0.6221 | 0.2107 |
| XGBoost | 0.6413 | 0.6248 | 0.2122 |

The 541,909 source rows included 5,268 exact duplicates and 135,080 missing customer identifiers. After filtering, 348,872 lines covered 3,916 customers. Median retained unit price was GBP 1.95. December 2011 is a partial month. See the [monthly plot](eda/online_retail_monthly.png).

## US survey test-retest benchmark

Twin-2K-500 supplied 40 repeated hypothetical pricing questions. We fit a question marginal and a smoothed transition model on 1,647 participants and evaluated 16,440 answers from 411 disjoint participants. The transition model conditions on that participant's earlier answer to the same item.

| Model | Log loss | Brier | Accuracy |
| --- | ---: | ---: | ---: |
| Question marginal | 0.6840 | 0.2454 | 56.95% |
| Prior-answer transition | 0.4364 | 0.1332 | 84.15% |

The participant-clustered 95% bootstrap interval for the Brier difference was −0.118 to −0.107. The exercise measures test-retest fidelity for repeated US survey questions. It provides no estimate of actual purchase behavior, unseen-task fidelity, or Indian snack choice. [Full metrics](twin2k_pricing_fidelity.json)

## Synthetic model check

| Choice fit | Log loss | Multiclass Brier | Accuracy |
| --- | ---: | ---: | ---: |
| Pooled conditional logit | 0.9209 | 0.5416 | 57.41% |
| Empirical Bayes segment model | 0.8715 | 0.5102 | 61.11% |

The [seeded split](sandbox_choice_benchmark.json) held out 108 tasks from 18 synthetic participants. The [policy experiment](choice_experiments.json) averaged eight synthetic replicates. At 24 responses, share MAE was 0.0843 random, 0.0740 balanced and 0.0708 adaptive. Candidate coverage was 95.0%, 100.0% and 22.5% respectively. The single-stream chronological updating check produced log losses of 0.9004 static, 0.8967 periodic refit, and 0.9025 sequential Laplace.

The full hierarchical PyMC check used 18 synthetic participants and four chains with 500 retained draws each. Maximum unrounded R-hat was 1.0088, minimum bulk or tail ESS was 633.7, and there were zero divergences. The observed no-purchase rate was 47.2%, within the replicated 90% interval of 38.0% to 57.4%. [Diagnostics](bayes_diagnostics.json)

These checks use simulated choice behavior. They do not establish predictive fidelity or sample efficiency on human data. Human choice fidelity, randomized price validation, and cross-city transfer are pending.
