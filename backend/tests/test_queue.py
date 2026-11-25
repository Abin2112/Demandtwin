import time

from celery import Celery
from celery.contrib.testing.worker import start_worker

from demandtwin_ml.synthetic import candidates

from test_workflow import client, register, send


def test_worker_claims_and_finishes_run(monkeypatch):
    from app import analytics, jobs

    queue = Celery("demandtwin_test", broker="memory://")
    monkeypatch.setattr(analytics, "train_task", queue.task(name="demandtwin.test.train")(jobs.execute))
    with start_worker(queue, pool="solo", perform_ping_check=False), client() as browser:
        register(browser)
        project = send(browser, "POST", "/projects", 201, json={"name": "Worker verification"})
        study = send(browser, "POST", "/experiments", 201, json={
            "project_id": project["id"], "name": "Queued study", "designs": candidates(),
        })
        path = "/experiments/" + study["id"]
        send(browser, "POST", path + "/launch")
        send(browser, "POST", path + "/seed", 201)
        run = send(browser, "POST", "/models/train", 202, json={"experiment_id": study["id"]})
        assert run["status"] == "queued"
        deadline = time.monotonic() + 20
        while run["status"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(0.2)
            run = send(browser, "GET", f"/models/{run['id']}/status")
        assert run["status"] == "ready", run
