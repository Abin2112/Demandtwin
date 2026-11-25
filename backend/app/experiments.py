import secrets
from collections import Counter
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from demandtwin_ml.choice import Observation, draws, rank_designs


from .config import ETHICS_CONSENT, ETHICS_PROTOCOL
from .assignment import assign_next, eligible_designs, policy_for, task_count
from .db import Design, Experiment, ModelRun, Participant, Project, Response, timestamp
from .schemas import Choice, Consent, DesignInput, ExperimentInput
from .security import Actor, DB, Researcher, digest
from .workspace import Page, accessible_projects, add, audit, listing, owned, project_for

router = APIRouter(tags=["experiments"])
ParticipantKey = Annotated[str, Header(alias="X-Participant-Key", min_length=30, max_length=128)]
RANDOM = secrets.SystemRandom()
SANDBOX_CONSENT = (
    "We store your selected shopping segment, randomly assigned tasks, choices and consent version. "
    "Participation is voluntary. Use the withdrawal button on this device to delete your responses."
)


def approved_protocol(row=None):
    return bool(ETHICS_PROTOCOL and ETHICS_CONSENT and (row is None or row.protocol == ETHICS_PROTOCOL))


def consent_content(row):
    if row.synthetic:
        return "v1", SANDBOX_CONSENT
    return "v1-" + digest(ETHICS_CONSENT)[:20], ETHICS_CONSENT


def experiment_view(row):
    return {"id": row.id, "project_id": row.project_id, "name": row.name, "status": row.status,
            "synthetic": row.synthetic, "protocol": row.protocol, "designs": row.designs, "created": timestamp(row.created),
            "policy": policy_for(row).model_dump(), "task_count": task_count(row)}


def participant_for(db, experiment_id, token):
    participant = db.scalar(select(Participant).where(
        Participant.experiment_id == str(experiment_id), Participant.token_hash == digest(token),
    ))
    if participant is None:
        raise HTTPException(404, "Participant session not found")
    return participant


def public_experiment(db, key):
    row = db.get(Experiment, str(key))
    if row is None or row.status != "active" or (not row.synthetic and not approved_protocol(row)):
        raise HTTPException(404, "Active study not found")
    return row


def choice_rows(db, experiment):
    query = select(Response, Participant).join(Participant).where(Participant.experiment_id == experiment.id)
    observations = []
    for response, participant in db.execute(query.order_by(Participant.id, Response.task)):
        assignment = participant.assignment[response.task]
        alternatives = [experiment.designs[assignment["design"]][idx] for idx in assignment["order"]]
        observations.append(Observation(participant.id, participant.segment, alternatives, response.chosen))
    return observations


@router.post("/experiments", status_code=201)
def create_experiment(body: ExperimentInput, db: DB, user: Actor):
    project = project_for(db, body.project_id, user)
    if not body.synthetic and (user.role != "researcher" or not approved_protocol()):
        raise HTTPException(403, "Real collection requires researcher access, an approved protocol and approved consent text")
    row = Experiment(project_id=project.id, name=body.name, synthetic=body.synthetic,
                     protocol=None if body.synthetic else ETHICS_PROTOCOL,
                     designs=[[alt.model_dump() for alt in design] for design in body.designs],
                     policy=body.policy.model_dump())
    if not eligible_designs(row):
        raise HTTPException(422, "No candidate tasks meet the study price and product limits")
    return experiment_view(add(db, user, "experiment.create", row))


@router.get("/experiments")
def experiments(db: DB, user: Actor, page: Page):
    query = select(Experiment).where(Experiment.project_id.in_(accessible_projects(user)))
    return [experiment_view(row) for row in listing(db, query, Experiment, page)]


@router.get("/experiments/{key}")
def experiment(key: UUID, db: DB, user: Actor):
    return experiment_view(owned(db, Experiment, key, user))


@router.post("/experiments/{key}/launch")
def launch(key: UUID, db: DB, user: Actor):
    row = owned(db, Experiment, key, user)
    if row.status == "closed":
        raise HTTPException(409, "Closed studies cannot be relaunched")
    if not row.synthetic and (user.role != "researcher" or not approved_protocol(row)):
        raise HTTPException(403, "Study protocol is unavailable")
    row.status = "active"
    audit(db, user, "experiment.launch", row.id)
    db.commit()
    return experiment_view(row)


@router.post("/experiments/{key}/close")
def close(key: UUID, db: DB, user: Actor):
    row = owned(db, Experiment, key, user)
    if row.status != "active":
        raise HTTPException(409, "Only active studies can be closed")
    row.status = "closed"
    audit(db, user, "experiment.close", row.id)
    db.commit()
    return experiment_view(row)


@router.get("/experiments/{key}/participant")
def study(key: UUID, db: DB):
    row = public_experiment(db, key)
    version, text = consent_content(row)
    return {"id": row.id, "name": row.name, "synthetic": row.synthetic, "task_count": task_count(row),
            "consent_version": version, "consent_text": text}


@router.post("/experiments/{key}/consent", status_code=201)
def consent(key: UUID, body: Consent, db: DB):
    row = public_experiment(db, key)
    # Serialize quota admission on both SQLite and PostgreSQL.
    db.execute(update(Experiment).where(Experiment.id == row.id).values(seeded=Experiment.seeded))
    db.refresh(row)
    if row.status != "active":
        raise HTTPException(409, "Study is no longer active")
    if row.synthetic != body.synthetic:
        raise HTTPException(409, "Consent does not match the study's evidence mode")
    if body.version != consent_content(row)[0]:
        raise HTTPException(409, "Consent version changed. Reload the study before continuing.")
    policy = policy_for(row)
    quota = policy.segment_quotas.get(body.segment)
    if policy.segment_quotas and quota is None:
        raise HTTPException(409, "This shopping segment is not being enrolled")
    enrolled = db.scalar(select(func.count()).select_from(Participant).where(
        Participant.experiment_id == row.id, Participant.segment == body.segment,
    ))
    if quota is not None and enrolled >= quota:
        raise HTTPException(409, "This shopping segment has reached its enrollment limit")
    token = secrets.token_urlsafe(48)
    assignments = []
    initial_count = task_count(row) if policy.strategy == "random" else 0
    for idx in RANDOM.sample(eligible_designs(row), initial_count):
        order = list(range(len(row.designs[idx])))
        RANDOM.shuffle(order)
        assignments.append({"design": idx, "order": order})
    db.add(Participant(experiment_id=row.id, token_hash=digest(token), segment=body.segment,
                       consent_version=body.version, assignment=assignments))
    db.commit()
    return {"participant_key": token}


@router.get("/experiments/{key}/tasks")
def tasks(key: UUID, db: DB, token: ParticipantKey):
    row = public_experiment(db, key)
    participant = participant_for(db, key, token)
    if policy_for(row).strategy != "random":
        participant = assign_next(db, row, participant, RANDOM)
    answered = set(db.scalars(select(Response.task).where(Response.participant_id == participant.id)))
    return [
        {"task": idx, "alternatives": [row.designs[item["design"]][alt] for alt in item["order"]]}
        for idx, item in enumerate(participant.assignment) if idx not in answered
    ]


@router.post("/experiments/{key}/responses", status_code=201)
def respond(key: UUID, body: Choice, db: DB, token: ParticipantKey):
    public_experiment(db, key)
    participant = participant_for(db, key, token)
    if body.task >= len(participant.assignment) or body.chosen > len(participant.assignment[body.task]["order"]):
        raise HTTPException(422, "Choice is outside the assigned task")
    db.add(Response(participant_id=participant.id, **body.model_dump()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Response).where(Response.participant_id == participant.id, Response.task == body.task))
        if existing is None or existing.chosen != body.chosen:
            raise HTTPException(409, "Choice could not be recorded") from None
    return {"recorded": True}


@router.delete("/experiments/{key}/participant", status_code=204)
def withdraw(key: UUID, db: DB, token: ParticipantKey):
    experiment = db.scalar(select(Experiment).where(Experiment.id == str(key)).with_for_update())
    participant = participant_for(db, key, token)
    db.delete(participant)
    if not experiment.synthetic:
        db.execute(delete(ModelRun).where(ModelRun.experiment_id == str(key)))
        db.execute(delete(Design).where(Design.experiment_id == str(key)))
    db.commit()


@router.get("/experiments/{key}/results")
def results(key: UUID, db: DB, user: Actor):
    row = owned(db, Experiment, key, user)
    participants = db.scalar(select(func.count()).select_from(Participant).where(Participant.experiment_id == row.id))
    observations = choice_rows(db, row)
    choices = Counter("No purchase" if item.chosen == 0 else item.alternatives[item.chosen - 1]["name"] for item in observations)
    return {"synthetic": row.synthetic, "participants": participants, "responses": len(observations),
            "complete": sum(count == task_count(row) for count in Counter(x.participant for x in observations).values()),
            "choices": dict(choices),
            "segments": dict(db.execute(select(Participant.segment, func.count()).where(
                Participant.experiment_id == row.id).group_by(Participant.segment)).all())}


@router.post("/experiments/{key}/seed", status_code=201)
def seed_sandbox(key: UUID, db: DB, user: Actor):
    row = owned(db, Experiment, key, user)
    if not row.synthetic or row.status != "active":
        raise HTTPException(409, "Seeding is restricted to active synthetic studies")
    # Use the same assumed utilities on the study's real design matrix.
    import numpy as np
    from demandtwin_ml.choice import SEGMENTS, design

    claimed = db.scalar(update(Experiment).where(
        Experiment.id == row.id, Experiment.synthetic.is_(True),
        Experiment.status == "active", Experiment.seeded.is_(False),
    ).values(seeded=True).returning(Experiment.id))
    if claimed is None:
        raise HTTPException(409, "The study already contains a generated panel or is no longer active")
    rng = np.random.default_rng(42)
    generated = 0
    quota = policy_for(row).segment_quotas
    enrolled = dict(db.execute(select(Participant.segment, func.count()).where(
        Participant.experiment_id == row.id).group_by(Participant.segment)).all())
    segments = [segment for segment in range(len(SEGMENTS))
                for _ in range(min(30, max(0, quota.get(SEGMENTS[segment], 0) - enrolled.get(SEGMENTS[segment], 0))) if quota else 30)]
    rng.shuffle(segments)
    for segment in segments:
        beta = np.array([0.6, -2.4 + 0.65 * segment, 0.7, 0.25, 0.2, -0.3 + segment * 0.25])
        beta += rng.normal(0, 0.24, len(beta))
        assignments = [
            {"design": int(k), "order": rng.permutation(len(row.designs[k])).tolist()}
            for k in rng.choice(eligible_designs(row), size=task_count(row), replace=False)
        ]
        participant = Participant(experiment_id=row.id, token_hash=digest(secrets.token_urlsafe(48)),
                                  segment=SEGMENTS[segment], consent_version="synthetic-generator-v1", assignment=assignments)
        db.add(participant)
        db.flush()
        for task, assignment in enumerate(assignments):
            alternatives = [row.designs[assignment["design"]][j] for j in assignment["order"]]
            chosen = int(np.argmax(design(alternatives) @ beta + rng.gumbel(size=len(alternatives) + 1)))
            db.add(Response(participant_id=participant.id, task=task, chosen=chosen))
        generated += 1
    audit(db, user, "experiment.seed", row.id)
    db.commit()
    return {"participants": generated, "synthetic": True}


@router.post("/experiments/{key}/next-design")
def next_design(key: UUID, body: DesignInput, db: DB, user: Actor):
    import numpy as np
    from demandtwin_ml.choice import FEATURES

    row = owned(db, Experiment, key, user)
    counts = Counter()
    for participant in db.scalars(select(Participant).where(Participant.experiment_id == row.id, Participant.segment == body.segment)):
        answered = db.scalars(select(Response.task).where(Response.participant_id == participant.id)).all()
        counts.update(participant.assignment[idx]["design"] for idx in answered)
    if body.model_id:
        model = owned(db, ModelRun, body.model_id, user)
        if model.status != "ready" or model.experiment_id != row.id:
            raise HTTPException(409, "Select a ready model for this experiment")
        samples = draws(model.artifact, body.segment, body.seed)
    else:
        samples = np.random.default_rng(body.seed).normal(0, 1, (512, len(FEATURES)))
    rankings = rank_designs(samples, row.designs, counts, body.strategy, body.seed)
    result = {"selected": rankings[0]["index"], "candidates": rankings, "segment": body.segment,
              "strategy": body.strategy, "model_id": str(body.model_id) if body.model_id else None,
              "rationale": {"adaptive": "Highest estimated information gain per displayed product",
                            "balanced": "Fewest completed tasks in this segment",
                            "random": "Seeded uniform ranking"}[body.strategy]}
    history = add(db, user, "experiment.design", Design(experiment_id=row.id, result=result))
    return {"id": history.id, **result}


@router.get("/experiments/{key}/design-history")
def design_history(key: UUID, db: DB, user: Actor, page: Page):
    row = owned(db, Experiment, key, user)
    query = select(Design).where(Design.experiment_id == row.id)
    return [{"id": item.id, "created": timestamp(item.created), **item.result} for item in listing(db, query, Design, page)]


@router.get("/experiments/{key}/export")
def export(key: UUID, db: DB, user: Researcher):
    row = owned(db, Experiment, key, user)
    observations = choice_rows(db, row)
    aliases = {person: f"p{i + 1}" for i, person in enumerate(sorted({x.participant for x in observations}))}
    return {"synthetic": row.synthetic, "evidence_type": "hypothetical_choice", "consent_protocol": row.protocol,
            "observations": [{"participant": aliases[x.participant], "segment": x.segment, "alternatives": x.alternatives,
                              "chosen": x.chosen, "synthetic": row.synthetic} for x in observations]}
