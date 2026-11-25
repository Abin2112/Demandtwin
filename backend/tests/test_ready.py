import io
from datetime import datetime, timedelta, timezone

from PIL import Image
from sqlalchemy.orm import Session

from demandtwin_ml.synthetic import candidates
from test_workflow import client, register, send


def test_collaboration_images_notifications_and_revocation():
    with client() as owner, client() as editor, client() as stranger:
        register(owner)
        credentials = register(editor)
        register(stranger)
        project = send(owner, "POST", "/projects", 201, json={"name": "Shared research"})
        assert project["created"].endswith("+00:00")
        root = "/projects/" + project["id"]
        person = send(owner, "POST", root + "/members", 201, json={"email": credentials["email"]})
        assert send(editor, "GET", "/projects")[0]["id"] == project["id"]
        send(editor, "DELETE", root, 404)
        send(editor, "POST", root + "/members", 404, json={"email": credentials["email"]})
        product = send(editor, "POST", "/products", 201, json={"project_id": project["id"], **candidates()[0][0]})
        path = "/products/" + product["id"] + "/image"
        png = io.BytesIO()
        source = Image.new("RGB", (20, 20), "#238060")
        metadata = source.getexif()
        metadata[271] = "Remove this camera metadata"
        source.save(png, format="JPEG", exif=metadata)
        send(editor, "POST", path, 415, content=b"<svg/>", headers={"Content-Type": "image/svg+xml"})
        send(editor, "POST", path, 422, content=b"invalid", headers={"Content-Type": "image/png"})
        uploaded = send(editor, "POST", path, content=png.getvalue(), headers={"Content-Type": "image/jpeg"})
        assert uploaded["packaging_image"] == "/api/v1" + path
        downloaded = send(owner, "GET", path)
        assert downloaded.headers["content-type"] == "image/png"
        with Image.open(io.BytesIO(downloaded.content)) as clean:
            assert not clean.getexif()
        send(stranger, "GET", path, 404)
        notifications = send(editor, "GET", "/notifications")
        assert notifications
        send(stranger, "POST", "/notifications/" + notifications[0]["id"] + "/read", 404)
        send(editor, "POST", "/notifications/" + notifications[0]["id"] + "/read")
        assert send(editor, "GET", "/notifications")[0]["read"]
        send(owner, "DELETE", root + "/members/" + person["id"], 204)
        assert send(editor, "GET", "/projects") == []
        send(editor, "GET", path, 404)
        assert send(editor, "GET", "/notifications") == []


def test_adaptive_session_budget_constraints_and_quota():
    with client() as owner, client() as guest:
        register(owner)
        project = send(owner, "POST", "/projects", 201, json={"name": "Adaptive"})
        study = send(owner, "POST", "/experiments", 201, json={
            "project_id": project["id"], "name": "Bounded assignment", "designs": candidates(),
            "policy": {"strategy": "adaptive", "task_limit": 3, "max_products": 2, "min_price": 15,
                       "max_price": 40, "segment_quotas": {"value": 1}},
        })
        root = "/experiments/" + study["id"]
        send(owner, "POST", root + "/launch")
        consent = {"adult": True, "consent": True, "version": "v1", "synthetic": True, "segment": "value"}
        token = send(guest, "POST", root + "/consent", 201, json=consent)
        send(guest, "POST", root + "/consent", 409, json=consent)
        send(guest, "POST", root + "/consent", 409, json={**consent, "segment": "premium"})
        headers = {"X-Participant-Key": token["participant_key"]}
        for index in range(3):
            tasks = send(guest, "GET", root + "/tasks", headers=headers)
            assert len(tasks) == 1
            assert tasks == send(guest, "GET", root + "/tasks", headers=headers)
            assert tasks[0]["task"] == index
            assert all(15 <= product["price"] <= 40 for product in tasks[0]["alternatives"])
            send(guest, "POST", root + "/responses", 201, json={"task": index, "chosen": 0}, headers=headers)
        assert send(guest, "GET", root + "/tasks", headers=headers) == []
        history = send(owner, "GET", root + "/design-history")
        assert len(history) == 3
        assert len({row["selected"] for row in history}) == 3
        assert send(owner, "GET", root + "/results")["complete"] == 1


def test_demo_is_reusable_and_interrupted_job_can_retry():
    from app.db import ModelRun, engine

    with client() as browser:
        register(browser)
        demo = send(browser, "POST", "/demo")
        assert demo["status"] == "ready"
        assert send(browser, "POST", "/demo") == demo
        assert len(send(browser, "GET", "/projects")) == 1
        assert len(send(browser, "GET", "/simulations")) == 3
        send(browser, "POST", "/models/" + demo["model_id"] + "/retry", 409)
        with Session(engine) as db:
            run = db.get(ModelRun, demo["model_id"])
            run.status = "running"
            run.started_at = datetime.now(timezone.utc) - timedelta(minutes=30)
            db.commit()
        retried = send(browser, "POST", "/models/" + demo["model_id"] + "/retry", 202)
        assert retried["status"] == "ready"
        assert retried["seed"] == 42
