import uuid

from fastapi.testclient import TestClient
import numpy as np

from demandtwin_ml.synthetic import candidates


def client():
    from app.main import app
    return TestClient(app)


def register(browser, research_code=None):
    credentials = {"email": f"{uuid.uuid4()}@example.test", "password": "unrelated-test-password"}
    data = {**credentials, **({"research_code": research_code} if research_code else {})}
    response = browser.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201, response.text
    return credentials


def send(browser, method, path, status=200, **kwargs):
    response = browser.request(method, "/api/v1" + path, **kwargs)
    assert response.status_code == status, response.text
    if response.content and response.headers.get("content-type") == "application/json":
        return response.json()
    return response


def test_full_workflow():
    designs = candidates()
    with client() as owner, client() as outsider, client() as participant:
        credentials = register(owner)
        register(outsider)
        send(owner, "GET", "/auth/me")
        old_refresh = owner.cookies.get("dt_refresh")
        send(owner, "POST", "/auth/refresh")
        assert owner.cookies.get("dt_refresh") != old_refresh
        send(participant, "POST", "/auth/refresh", 401, headers={"Cookie": "dt_refresh=" + old_refresh})
        project = send(owner, "POST", "/projects", 201, json={"name": "Mumbai snack tests"})
        key = project["id"]
        send(outsider, "GET", f"/projects/{key}", 404)
        send(owner, "PATCH", f"/projects/{key}", json={"name": "Mumbai crisps"})
        product = send(owner, "POST", "/products", 201, json={"project_id": key, **designs[0][0], "competitors": designs[0][1:]})
        variant = send(owner, "POST", f"/products/{product['id']}/variants", 201, json={**designs[0][0], "price": 25})
        assert variant["parent_id"] == product["id"]
        send(owner, "POST", "/products", 422, json={"project_id": key, **designs[0][0], "price": -10})
        spec = {"name": "Price tests", "project_id": key, "designs": designs}
        send(owner, "POST", "/experiments", 403, json={**spec, "synthetic": False})
        study = send(owner, "POST", "/experiments", 201, json=spec)
        route = f"/experiments/{study['id']}"
        send(participant, "GET", route + "/participant", 404)
        send(owner, "POST", route + "/launch")
        send(participant, "POST", route + "/consent", 422, json={"segment": "value", "adult": False, "consent": True, "version": "v1", "synthetic": True})
        token = send(participant, "POST", route + "/consent", 201, json={"segment": "value", "adult": True, "consent": True, "version": "v1", "synthetic": True})
        headers = {"X-Participant-Key": token["participant_key"]}
        tasks = send(participant, "GET", route + "/tasks", headers=headers)
        assert len(tasks) == 6
        for item in tasks:
            send(participant, "POST", route + "/responses", 201, json={"task": item["task"], "chosen": 0}, headers=headers)
        send(participant, "POST", route + "/responses", 201, json={"task": tasks[0]["task"], "chosen": 0}, headers=headers)
        send(participant, "POST", route + "/responses", 409, json={"task": tasks[0]["task"], "chosen": 1}, headers=headers)
        assert send(owner, "GET", route + "/results")["responses"] == 6
        send(participant, "DELETE", route + "/participant", 204, headers=headers)
        assert send(owner, "GET", route + "/results")["responses"] == 0
        failed = send(owner, "POST", "/models/train", 202, json={"experiment_id": study["id"]})
        assert failed["status"] == "failed"
        send(owner, "POST", route + "/seed", 201)
        send(owner, "POST", route + "/seed", 409)
        assert send(owner, "GET", route + "/results")["responses"] == 540
        run = send(owner, "POST", "/models/train", 202, json={"experiment_id": study["id"]})
        assert run["status"] == "ready", run
        assert run["test_rows"] == 108
        assert run["synthetic"]
        model_id = run["id"]
        rank = send(owner, "POST", route + "/next-design", json={"model_id": model_id})
        assert len(rank["candidates"]) == len(designs)
        assert send(owner, "GET", route + "/design-history")[0]["id"] == rank["id"]
        base = {"name": "Base", "product": designs[1][0], "competitors": designs[1][1:],
                "opportunities": 5000, "segment_weights": {"balanced": 1, "value": 2}}
        simulation = send(owner, "POST", "/simulations", 201, json={**base, "model_id": model_id})
        assert np.isclose(sum(simulation["result"]["choice"]), 1)
        assert np.isclose(simulation["result"]["choice"][1] * 5000, simulation["result"]["expected_units"][0])
        assert simulation["result"]["synthetic"]
        compare = send(owner, "POST", "/simulations/compare", 201, json={"model_id": model_id, "scenarios": [
            base, {**base, "name": "Extrapolation", "product": {**base["product"], "price": 80}},
        ]})
        assert compare[1]["result"]["abstain"]
        report = send(owner, "POST", "/reports", 201, json={"simulation_id": simulation["id"]})
        pdf = send(owner, "GET", f"/reports/{report['id']}/download")
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF")
        send(outsider, "GET", f"/reports/{report['id']}/download", 404)
        overview = send(owner, "GET", "/dashboard")
        assert overview["real_participants"] == 0
        assert overview["synthetic_participants"] == 90
        send(owner, "POST", route + "/close")
        send(owner, "POST", "/auth/logout", 204)
        send(owner, "GET", "/auth/me", 401)
        send(owner, "POST", "/auth/login", json=credentials)
        send(owner, "DELETE", f"/projects/{key}", 204)
        send(owner, "GET", f"/models/{model_id}", 404)


def test_research_access():
    with client() as founder, client() as researcher:
        register(founder)
        register(researcher, "isolated-test-code")
        send(founder, "GET", "/research/datasets", 403)
        datasets = send(researcher, "GET", "/research/datasets")
        assert any(row["id"] == "online_retail" for row in datasets)
        send(researcher, "GET", "/research/exports")
