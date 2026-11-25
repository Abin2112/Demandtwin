# RACE-Twin · Manuscript draft

## Abstract

We propose an evidence-aware choice modeling and adaptive experimental design framework for packaged snacks. The current implementation supports protocol-gated consent, choice collection, conditional simulation and evidence-labeled exports. Human efficacy results are pending.

## Introduction

Demand estimation for a new concept requires defining the opportunity and plausible alternatives before mapping preferences to predicted choice.

## Related work and gap

See the [literature review](../literature_review/Literature_Review.md). The study will examine whether aligned purchase evidence and constrained adaptive designs improve conditional prediction.

## Methodology and mathematical formulation

See the [methodology](../methodology/Research_Methodology.md) and [mathematical formulation](../mathematical_models/Mathematical_Formulation.md).

## Datasets and experimental setup

Use the [catalogue](../../data/metadata/dataset_catalogue.json) to distinguish the UK transaction benchmark, the US survey test-retest benchmark, sandbox tasks and future prospective human studies. The UK target is repeat activity. The US target is the response to a repeated hypothetical pricing item. The snack choice setup includes the outside option and grouped-participant evaluation.

## Results and ablations

Prospective human results and ablations are pending. The [engineering experiment report](../results/EXPERIMENT_REPORT.md) contains reproducible external benchmark and synthetic checks, under separate target definitions.

## Discussion and limitations

The engineering checks test implementation and uncertainty plumbing. Preference fidelity, purchase calibration, causal price effects, sample efficiency and population transfer require prospective evidence. See [limitations](../limitations/Limitations.md).

## Ethics

Human recruitment is subject to an approved [protocol](../ethics/PROTOCOL.md).

## Conclusion and references

The proposed framework is available for empirical study. Verified methodological references are listed in the [literature review](../literature_review/Literature_Review.md).
