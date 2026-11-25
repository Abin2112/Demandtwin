"""Persisted assignment with a per-participant task budget and segment quotas."""
from collections import Counter

import numpy as np
from fastapi import HTTPException
from sqlalchemy import select, update

from demandtwin_ml.choice import FEATURES, Observation, parameter, posterior, rank_designs

from .db import Design, ModelRun, Participant, Response
from .schemas import StudyPolicy


def policy_for(study):
    return StudyPolicy.model_validate(study.policy or {})


def eligible_designs(study):
    policy = policy_for(study)
    return [idx for idx, alternatives in enumerate(study.designs)
            if len(alternatives) <= policy.max_products
            and all(policy.min_price <= alt["price"] <= policy.max_price for alt in alternatives)]


def task_count(study):
    return min(policy_for(study).task_limit, len(eligible_designs(study)))


def assign_next(db, study, participant, random):
    """An optimistic update prevents concurrent reloads from appending two tasks."""
    original = participant.assignment
    original_version = participant.assignment_version
    answered = db.scalars(select(Response).where(Response.participant_id == participant.id)).all()
    if len(answered) < len(original) or len(original) >= task_count(study):
        return participant
    policy = policy_for(study)
    exposure = Counter()
    for other in db.scalars(select(Participant).where(
        Participant.experiment_id == study.id, Participant.segment == participant.segment,
    )):
        exposure.update(item["design"] for item in other.assignment)
    available = [idx for idx in eligible_designs(study) if idx not in {item["design"] for item in original}]
    model = db.scalar(select(ModelRun).where(
        ModelRun.experiment_id == study.id, ModelRun.status == "ready",
    ).order_by(ModelRun.created.desc()).limit(1))
    # Use the latest segment fit as an empirical prior and condition on this
    # session's choices. Uncertainty retains the Laplace approximation.
    if model:
        group = parameter(model.artifact, participant.segment)
        mean, covariance = group["mean"], np.asarray(group["covariance"]) + 0.75 * np.eye(len(FEATURES))
    else:
        mean, covariance = np.zeros(len(FEATURES)), np.eye(len(FEATURES))
    rows = []
    for response in answered:
        assigned = original[response.task]
        alternatives = [study.designs[assigned["design"]][idx] for idx in assigned["order"]]
        rows.append(Observation(participant.id, participant.segment, alternatives, response.chosen))
    try:
        preferences = posterior(mean, covariance, rows)
    except ValueError:
        raise HTTPException(503, "The next task could not be selected. Please retry.") from None
    seed = random.randrange(2**32)
    samples = np.random.default_rng(seed).multivariate_normal(preferences["mean"], preferences["covariance"], size=256)
    candidates = [study.designs[idx] for idx in available]
    rankings = rank_designs(samples, candidates, {i: exposure[idx] for i, idx in enumerate(available)}, policy.strategy, seed)
    if policy.strategy == "adaptive":
        for item in rankings:
            item["score"] /= (1 + item["completed"]) ** policy.coverage_penalty
        rankings.sort(key=lambda item: item["score"], reverse=True)
    selected = available[rankings[0]["index"]]
    order = list(range(len(study.designs[selected])))
    random.shuffle(order)
    assignments = [*original, {"design": selected, "order": order}]
    claimed = db.scalar(update(Participant).where(
        Participant.id == participant.id, Participant.assignment_version == original_version,
    ).values(assignment=assignments, assignment_version=original_version + 1)
     .returning(Participant.id))
    if claimed is not None:
        db.add(Design(experiment_id=study.id, result={
            "strategy": policy.strategy, "segment": participant.segment,
            "selected": selected, "model_id": model.id if model else None,
            "rationale": "Participant assignment within task, price and burden limits",
            "seed": seed, "task": len(original), "information_gain_nats": rankings[0]["information_gain_nats"],
            "candidates": [{**item, "index": available[item["index"]]} for item in rankings],
        }))
        db.commit()
    else:
        db.rollback()
    db.refresh(participant)
    return participant
