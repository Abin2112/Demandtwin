"""Purchase-anchored preference updates for aligned research choice panels."""
from dataclasses import dataclass
from typing import Literal

import numpy as np

from .choice import FEATURES, Observation, posterior

EvidenceKind = Literal["stated_preference", "hypothetical_choice", "incentivized_choice", "actual_purchase", "repeat_purchase"]
KINDS = ("stated_preference", "hypothetical_choice", "incentivized_choice", "actual_purchase", "repeat_purchase")


@dataclass(frozen=True)
class Evidence:
    observation: Observation
    kind: EvidenceKind
    dataset_version: str
    synthetic: bool
    choice_set_observed: bool


def anchored_preferences(records, *, transfer_variance=1.0, min_overlap=8):
    """Fit a purchase reference and separate channel/participant deviations.

    Each row must describe a discrete choice with the observed alternatives,
    including the outside option. Stated scores and receipt-only observations
    require different likelihoods and are ineligible here.
    """
    if not records or transfer_variance <= 0 or min_overlap < 2:
        raise ValueError("Provide observations, positive transfer variance and a valid overlap threshold")
    if any(row.kind not in KINDS or not row.dataset_version or not row.choice_set_observed for row in records):
        raise ValueError("Evidence must have known provenance and an observed choice set")
    if len({row.synthetic for row in records}) > 1:
        raise ValueError("Synthetic and human evidence must stay in separate fits")
    reference = [row.observation for row in records if row.kind == "actual_purchase"]
    anchored_people = {row.participant for row in reference}
    if len(anchored_people) < min_overlap or not any(row.chosen == 0 for row in reference):
        raise ValueError("An aligned actual-purchase choice panel with observed outside selections is required")
    center = posterior(np.zeros(len(FEATURES)), np.eye(len(FEATURES)) * 9, reference)
    channels = {"actual_purchase": center}
    coverage = {}
    for kind in KINDS:
        channel = [row.observation for row in records if row.kind == kind]
        aligned = [row for row in channel if row.participant in anchored_people]
        overlap = len({row.participant for row in aligned})
        coverage[kind] = {"rows": len(channel), "aligned_participants": overlap}
        if kind != "actual_purchase" and overlap >= min_overlap:
            channels[kind] = posterior(center["mean"], np.asarray(center["covariance"]) + transfer_variance * np.eye(len(FEATURES)), aligned)
    return {
        "synthetic": records[0].synthetic, "channels": channels, "coverage": coverage,
        "versions": sorted({row.dataset_version for row in records}),
        "method": "purchase-anchored channel-specific Laplace fits",
    }


def update_individual(segment_posterior, observations, heterogeneity_variance=0.75):
    """Update one participant with an explicitly selected evidence channel."""
    if heterogeneity_variance <= 0 or len({row.participant for row in observations}) > 1:
        raise ValueError("Use a positive heterogeneity variance and one participant")
    covariance = np.asarray(segment_posterior["covariance"]) + heterogeneity_variance * np.eye(len(FEATURES))
    return posterior(segment_posterior["mean"], covariance, observations)
