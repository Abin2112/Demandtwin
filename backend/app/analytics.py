import io
import json
import logging
from html import escape
from uuid import UUID
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, func, or_, select, update

from demandtwin_ml.choice import scenario

from .config import ROOT
from .db import Experiment, ModelRun, Participant, Product, Report, Simulation, timestamp
from .jobs import execute, train_task
from .schemas import Comparison, ReportInput, SimulationInput, Training
from .security import Actor, DB, Researcher
from .workspace import Page, accessible_projects, add, audit, listing, notify, owned

router = APIRouter(tags=["analytics"])
logger = logging.getLogger(__name__)


def model_view(row):
    return {"id": row.id, "project_id": row.project_id, "experiment_id": row.experiment_id, "status": row.status,
            "created": timestamp(row.created), "started_at": timestamp(row.started_at), **row.result}


def ready(row):
    if row.status != "ready":
        raise HTTPException(409, "A successfully trained model is required")
    return row


@router.post("/models/train", status_code=202)
def train(body: Training, db: DB, user: Actor):
    experiment = owned(db, Experiment, body.experiment_id, user)
    run = add(db, user, "model.train", ModelRun(project_id=experiment.project_id, experiment_id=experiment.id,
                                                status="queued", result={"synthetic": experiment.synthetic, "seed": body.seed}))
    dispatch(db, run, body.seed)
    return model_view(run)


def dispatch(db, run, seed):
    if train_task is None:
        execute(run.id, seed)
        db.refresh(run)
    else:
        try:
            train_task.apply_async(args=(run.id, seed), retry=False)
        except Exception:
            logger.exception("Could not queue model run %s", run.id)
            run.status, run.result = "failed", {**run.result, "error": "Training queue unavailable"}
            db.commit()
            raise HTTPException(503, "Training queue unavailable") from None


@router.post("/models/{key}/retry", status_code=202)
def retry_model(key: UUID, db: DB, user: Actor):
    row = owned(db, ModelRun, key, user)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=20)
    eligible = or_(
        ModelRun.status == "failed",
        and_(ModelRun.status == "queued", ModelRun.created < cutoff),
        and_(ModelRun.status == "running", or_(ModelRun.started_at < cutoff, ModelRun.started_at.is_(None))),
    )
    changed = db.scalar(update(ModelRun).where(ModelRun.id == row.id, eligible)
                        .values(status="queued", started_at=None, claim=None, artifact={})
                        .execution_options(synchronize_session=False)
                        .returning(ModelRun.id))
    if changed is None:
        raise HTTPException(409, "Only failed or interrupted runs older than 20 minutes can be retried")
    row.result = {key: value for key, value in row.result.items() if key != "error"}
    audit(db, user, "model.retry", row.id)
    db.commit()
    db.refresh(row)
    dispatch(db, row, row.result.get("seed", 42))
    return model_view(row)


@router.get("/models")
def models(db: DB, user: Actor, page: Page):
    query = select(ModelRun).where(ModelRun.project_id.in_(accessible_projects(user)))
    return [model_view(row) for row in listing(db, query, ModelRun, page)]


@router.get("/models/{key}")
def model(key: UUID, db: DB, user: Actor):
    row = owned(db, ModelRun, key, user)
    return {**model_view(row), "preferences": row.artifact}


@router.get("/models/{key}/metrics")
def model_metrics(key: UUID, db: DB, user: Actor):
    return ready(owned(db, ModelRun, key, user)).result["metrics"]


@router.get("/models/{key}/status")
def model_status(key: UUID, db: DB, user: Actor):
    return model_view(owned(db, ModelRun, key, user))


def simulate(run, body):
    data = body.model_dump(mode="json", exclude={"model_id"})
    alternatives = [data["product"], *data["competitors"]]
    estimate = scenario(run.artifact, alternatives, body.segment_weights, body.opportunities)
    estimate.update(synthetic=run.result["synthetic"], evidence_quality=run.result["evidence_quality"],
                    labels=["No purchase", *[alternative["name"] for alternative in alternatives]])
    if run.result["synthetic"]:
        estimate["warnings"].append("Synthetic choice evidence. Sandbox use only.")
    else:
        estimate["warnings"].append("Local hypothetical choices. Market representativeness and purchase conversion are unverified.")
    return Simulation(project_id=run.project_id, model_id=run.id, name=body.name, inputs=data, result=estimate)


def simulation_view(row):
    return {"id": row.id, "name": row.name, "model_id": row.model_id, "created": timestamp(row.created), "inputs": row.inputs, "result": row.result}


@router.post("/simulations", status_code=201)
def create_simulation(body: SimulationInput, db: DB, user: Actor):
    run = ready(owned(db, ModelRun, body.model_id, user))
    return simulation_view(add(db, user, "simulation.create", simulate(run, body)))


@router.post("/simulations/compare", status_code=201)
def compare(body: Comparison, db: DB, user: Actor):
    from .workspace import audit

    run = ready(owned(db, ModelRun, body.model_id, user))
    simulations = [simulate(run, item) for item in body.scenarios]
    db.add_all(simulations)
    db.flush()
    for row in simulations:
        audit(db, user, "simulation.create", row.id)
    notify(db, run.project_id, "A scenario comparison has been saved.")
    db.commit()
    return [simulation_view(row) for row in simulations]


@router.get("/simulations")
def simulations(db: DB, user: Actor, page: Page):
    query = select(Simulation).where(Simulation.project_id.in_(accessible_projects(user)))
    return [simulation_view(row) for row in listing(db, query, Simulation, page)]


@router.get("/simulations/{key}")
@router.get("/simulations/{key}/results")
def get_simulation(key: UUID, db: DB, user: Actor):
    return simulation_view(owned(db, Simulation, key, user))


@router.get("/dashboard")
def dashboard(db: DB, user: Actor):
    project_ids = accessible_projects(user)
    product_count = db.scalar(select(func.count()).select_from(Product).where(Product.project_id.in_(project_ids)))
    study_counts = dict(db.execute(select(Experiment.status, func.count()).where(Experiment.project_id.in_(project_ids)).group_by(Experiment.status)).all())
    people = db.execute(select(Experiment.synthetic, func.count()).select_from(Participant).join(Experiment).where(
        Experiment.project_id.in_(project_ids),
    ).group_by(Experiment.synthetic)).all()
    latest_model = db.scalar(select(ModelRun).where(ModelRun.project_id.in_(project_ids)).order_by(ModelRun.created.desc()).limit(1))
    latest_sim = db.scalar(select(Simulation).where(Simulation.project_id.in_(project_ids)).order_by(Simulation.created.desc()).limit(1))
    activity = listing(db, select(Experiment).where(Experiment.project_id.in_(project_ids)), Experiment, (5, 0))
    return {"products": product_count, "active": study_counts.get("active", 0), "completed": study_counts.get("closed", 0),
            "real_participants": dict(people).get(False, 0), "synthetic_participants": dict(people).get(True, 0),
            "model": model_view(latest_model) if latest_model else None,
            "simulation": simulation_view(latest_sim) if latest_sim else None,
            "activity": [{"id": row.id, "name": row.name, "status": row.status, "synthetic": row.synthetic} for row in activity]}


@router.get("/research/datasets")
def datasets(user: Researcher):
    return json.loads((ROOT / "data/metadata/dataset_catalogue.json").read_text(encoding="utf-8"))


@router.get("/research/training-runs")
def research_runs(db: DB, user: Researcher, page: Page):
    return models(db, user, page)


@router.get("/research/metrics")
def research_metrics(db: DB, user: Researcher, page: Page):
    return [item for item in models(db, user, page) if item["status"] == "ready"]


@router.get("/research/ablation")
def ablations(user: Researcher):
    path = ROOT / "research/results/choice_experiments.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "pending", "reason": "Run the offline experiment suite"}


@router.get("/research/exports")
def research_export(db: DB, user: Researcher, page: Page):
    return {"datasets": datasets(user), "training_runs": models(db, user, page), "experiments": ablations(user)}


def report_view(row):
    return {"id": row.id, "simulation_id": row.simulation_id, "created": timestamp(row.created)}


@router.post("/reports", status_code=201)
def create_report(body: ReportInput, db: DB, user: Actor):
    simulation = owned(db, Simulation, body.simulation_id, user)
    return report_view(add(db, user, "report.create", Report(project_id=simulation.project_id, simulation_id=simulation.id)))


@router.get("/reports")
def reports(db: DB, user: Actor, page: Page):
    query = select(Report).where(Report.project_id.in_(accessible_projects(user)))
    return [report_view(row) for row in listing(db, query, Report, page)]


@router.get("/reports/{key}")
def get_report(key: UUID, db: DB, user: Actor):
    return report_view(owned(db, Report, key, user))


@router.get("/reports/{key}/download")
def download_report(key: UUID, db: DB, user: Actor):
    report = owned(db, Report, key, user)
    simulation = db.get(Simulation, report.simulation_id)
    run = db.get(ModelRun, simulation.model_id)
    output = io.BytesIO()
    style = getSampleStyleSheet()
    estimate, data = simulation.result, simulation.inputs
    story = []

    def paragraph(text, heading="BodyText"):
        story.append(Paragraph(escape(str(text).replace("₹", "INR ")), style[heading]))

    paragraph("DemandTwin | Market scenario", "Title")
    paragraph(simulation.name, "Heading2")
    paragraph(f"{estimate['evidence_quality'].upper()} | Model {simulation.model_id}")
    paragraph(f"{data['product']['name']} · INR {data['product']['price']:g} · {data['product']['grams']:g} g")
    paragraph(f"Opportunity assumption: {data['opportunities']:,} eligible choice occasions.")
    paragraph(f"Method: grouped-participant holdout, then empirical Bayes Laplace refit on all eligible choices. Evidence: {run.result['evidence_type']}.")
    paragraph(f"Training coverage: {run.result['train_rows']} training and {run.result['test_rows']} holdout choice tasks.")
    story.append(Spacer(1, 12))
    table = [["Alternative", "Share", "90% share interval", "Expected units", "90% unit interval"]]
    for i, name in enumerate(estimate["labels"]):
        lo, hi = estimate["interval_90"][i]
        units, interval = "-", "-"
        if i:
            units = f"{estimate['expected_units'][i-1]:,.1f}"
            unit_low, unit_high = estimate["units_interval_90"][i-1]
            interval = f"{unit_low:,.1f} to {unit_high:,.1f}"
        table.append([Paragraph(escape(name.replace("₹", "INR ")), style["BodyText"]),
                      f"{estimate['choice'][i]:.1%}", f"{lo:.1%} to {hi:.1%}", units, interval])
    result_table = Table(table, colWidths=[118, 45, 91, 76, 103], repeatRows=1, hAlign="LEFT")
    result_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173d35")),
                                      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                      ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(result_table)
    paragraph("Evidence and limitations", "Heading2")
    for warning in estimate["warnings"]:
        paragraph(warning)
    paragraph(estimate["interpretation"])
    paragraph("Segment mix: " + ", ".join(f"{name} {value['weight']:.0%}" for name, value in estimate["segments"].items()))
    for name, value in estimate["segments"].items():
        paragraph(f"{name.title()} · target share {value['choice'][1]:.1%} · price utility coefficient {value['price_coefficient']:.3f} per INR.")
    SimpleDocTemplate(output, title="DemandTwin market scenario").build(story)
    return Response(output.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="demandtwin-{key}.pdf"', "Cache-Control": "private, no-store"})
