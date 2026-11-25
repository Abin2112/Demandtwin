import logging
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.orm import Session

from demandtwin_ml.choice import train

from .config import BROKER
from .db import Experiment, ModelRun, engine
from .experiments import choice_rows
from .workspace import notify

logger = logging.getLogger(__name__)


def execute(key, seed):
    claim = str(uuid4())
    with Session(engine) as db:
        experiment_id = db.scalar(update(ModelRun).where(ModelRun.id == key, ModelRun.status == "queued")
                                  .values(status="running", claim=claim, started_at=datetime.now(timezone.utc))
                                  .execution_options(synchronize_session=False)
                                  .returning(ModelRun.experiment_id))
        if experiment_id is None:
            return
        db.commit()
        experiment = db.get(Experiment, experiment_id)
        if experiment is None:
            return
        provenance = {"synthetic": experiment.synthetic, "seed": seed, "evidence_type": "hypothetical_choice",
                      "study_id": experiment.id, "protocol": experiment.protocol}
        try:
            observations = choice_rows(db, experiment)
            db.rollback()
            snapshot = json.dumps([asdict(row) for row in observations], sort_keys=True, separators=(",", ":"))
            provenance["dataset_version"] = hashlib.sha256(snapshot.encode()).hexdigest()
            artifact, result = train(observations, seed)
            result.update(provenance, training_time=datetime.now(timezone.utc).isoformat(),
                          features=artifact["features"], feature_version=artifact["feature_version"],
                          packages={pkg: version(pkg) for pkg in ("numpy", "scipy")},
                          evidence_quality="synthetic sandbox" if provenance["synthetic"] else "local hypothetical choices")
            status = "ready"
        except ValueError as exc:
            artifact, result, status = {}, {**provenance, "error": str(exc)}, "failed"
        except Exception:
            logger.exception("Training failed for run %s", key)
            artifact, result, status = {}, {**provenance, "error": "Model training failed. See server logs."}, "failed"
        project_id = db.scalar(update(ModelRun).where(
            ModelRun.id == key, ModelRun.claim == claim, ModelRun.status == "running",
        ).values(status=status, result=result, artifact=artifact).returning(ModelRun.project_id))
        if project_id is not None:
            notify(db, project_id, "Choice model training completed." if status == "ready" else "Choice model training failed. Review the run and retry.")
            db.commit()


if BROKER:
    from celery import Celery

    worker = Celery("demandtwin", broker=BROKER)
    worker.conf.update(
        task_acks_late=True, task_reject_on_worker_lost=True, worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        broker_transport_options={"visibility_timeout": 1800},
    )
    train_task = worker.task(name="demandtwin.train", soft_time_limit=840, time_limit=900)(execute)
else:
    worker = None
    train_task = None
