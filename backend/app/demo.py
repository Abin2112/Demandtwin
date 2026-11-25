"""Create a reproducible, explicitly synthetic workspace for a signed-in user."""
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from demandtwin_ml.synthetic import candidates

from .analytics import create_simulation, train
from .db import Experiment, ModelRun, Product, Project, Simulation
from .experiments import seed_sandbox
from .schemas import SimulationInput, Training
from .security import Actor, DB
from .workspace import audit

router = APIRouter(tags=["demo"])


@router.post("/demo")
def prepare_demo(db: DB, user: Actor):
    ids = {kind: str(uuid5(NAMESPACE_URL, f"demandtwin/demo/v1/{user.id}/{kind}"))
           for kind in ("project", "product", "study")}
    project = db.get(Project, ids["project"])
    if project is None:
        options = candidates()
        product, competitor = options[1]
        db.add(Project(id=ids["project"], owner_id=user.id, name="Demo · Mumbai snack sandbox",
                       description="Synthetic choice data for exploring DemandTwin."))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Demo preparation is already in progress. Retry shortly.") from None
        db.add(Product(id=ids["product"], project_id=ids["project"], name=product["name"], attributes={
            **{key: value for key, value in product.items() if key != "name"},
            "category": "Packaged snacks", "location": "Mumbai", "segment": "balanced",
            "description": "Synthetic demonstration concept", "ingredients": "Illustrative millet snack",
            "features": "", "cost": None, "packaging_image": None, "competitors": [competitor],
        }))
        study = Experiment(id=ids["study"], project_id=ids["project"], name="Demo · Synthetic price study",
                           status="active", synthetic=True, seeded=False, designs=options,
                           policy={"strategy": "adaptive", "task_limit": 6}, protocol=None)
        db.add(study)
        db.flush()
        audit(db, user, "demo.create", project.id if project else ids["project"])
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Demo preparation is already in progress. Retry shortly.") from None
    study = db.get(Experiment, ids["study"])
    if study is None:
        raise HTTPException(409, "The demo study was removed. Delete the demo project before preparing a new one.")
    if not study.seeded:
        seed_sandbox(study.id, db, user)
    run = db.scalar(select(ModelRun).where(ModelRun.experiment_id == study.id)
                    .order_by(ModelRun.created.desc()).limit(1))
    if run is None:
        training = train(Training(experiment_id=study.id), db, user)
        run = db.get(ModelRun, training["id"])
    if run.status == "ready":
        existing = db.scalars(select(Simulation).where(Simulation.model_id == run.id)).all()
        for price in (20, 30, 40):
            if any(item.inputs["product"]["price"] == price for item in existing):
                continue
            target, competitor = candidates()[1]
            create_simulation(SimulationInput.model_validate({
                "model_id": run.id, "name": f"Demo · INR {price}", "product": {**target, "price": price},
                "competitors": [competitor], "opportunities": 1000, "segment_weights": {"balanced": 1},
            }), db, user)
    return {"project_id": ids["project"], "study_id": study.id, "model_id": run.id,
            "status": run.status, "synthetic": True}
