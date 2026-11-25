# Limitations

- The UCI data represents historical transactions from one UK retailer, with missing customer identifiers, duplicate lines and cancellations. The label is observed repeat activity at that retailer.
- The synthetic utility generator couples several attributes. Coefficients for correlated features are weakly identifiable and can depend heavily on priors.
- The native simulator uses hypothetical choices and an assumed opportunity count. Real demand would require defensible coverage, frequency and conversion measurements.
- Purchase anchoring requires aligned participants and observed alternatives. No eligible aligned human purchase panel was acquired.
- Marginal range checks cannot detect all unsupported combinations. Local Laplace intervals omit uncertainty from survey sampling and the estimated segment prior.
- The offline single-segment adaptive check showed concentrated candidate exposure. Human efficiency, fairness, causal price effects and cross-city transfer remain untested.
