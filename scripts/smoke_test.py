"""Exercise a running API, including its configured training worker."""
import argparse
import io
import json
from pathlib import Path
import secrets
import sys
import time
from uuid import uuid4

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-engine"))
from demandtwin_ml.synthetic import candidates


def smoke(url, require_queue=False):
    project_id = None
    with httpx.Client(base_url=url.rstrip("/") + "/api/v1", timeout=120) as browser:
        def request(method, path, expected=200, **kwargs):
            response = browser.request(method, path, **kwargs)
            if response.status_code != expected:
                raise RuntimeError(f"{method} {path} returned {response.status_code}: {response.text[:250]}")
            return response

        health = request("GET", "/health").json()
        request("POST", "/auth/register", 201, json={
            "email": f"smoke-{uuid4()}@example.test", "password": secrets.token_urlsafe(30),
        })
        try:
            project = request("POST", "/projects", 201, json={"name": "Automated readiness check"}).json()
            project_id = project["id"]
            if not project["created"].endswith("+00:00"):
                raise RuntimeError("API timestamps must include their UTC offset")
            options = candidates()
            product = request("POST", "/products", 201, json={"project_id": project_id, **options[0][0]}).json()
            png = io.BytesIO()
            Image.new("RGB", (20, 20), "#238060").save(png, "PNG")
            request("POST", f"/products/{product['id']}/image", content=png.getvalue(), headers={"Content-Type": "image/png"})
            request("GET", f"/products/{product['id']}/image")
            study = request("POST", "/experiments", 201, json={
                "name": "Synthetic worker check", "project_id": project_id, "designs": options,
                "policy": {"strategy": "adaptive", "task_limit": 3},
            }).json()
            root = "/experiments/" + study["id"]
            request("POST", root + "/launch")
            request("POST", root + "/seed", 201)
            run = request("POST", "/models/train", 202, json={"experiment_id": study["id"]}).json()
            initial = run["status"]
            if require_queue and initial != "queued":
                raise RuntimeError("This check requires Redis-backed queued training")
            deadline = time.monotonic() + 120
            while run["status"] in {"queued", "running"} and time.monotonic() < deadline:
                time.sleep(0.5)
                run = request("GET", "/models/" + run["id"] + "/status").json()
            if run["status"] != "ready":
                raise RuntimeError(f"Training did not complete: {run}")
            simulation = request("POST", "/simulations", 201, json={
                "model_id": run["id"], "name": "Readiness scenario", "product": options[0][0],
                "competitors": options[0][1:], "opportunities": 1000, "segment_weights": {"balanced": 1},
            }).json()
            if abs(sum(simulation["result"]["choice"]) - 1) > 1e-8:
                raise RuntimeError("Choice probabilities did not normalize")
            report = request("POST", "/reports", 201, json={"simulation_id": simulation["id"]}).json()
            pdf = request("GET", "/reports/" + report["id"] + "/download")
            if not pdf.content.startswith(b"%PDF"):
                raise RuntimeError("Report download was not a PDF")
            token = request("POST", root + "/consent", 201, json={
                "adult": True, "consent": True, "version": "v1", "synthetic": True, "segment": "balanced",
            }).json()["participant_key"]
            headers = {"X-Participant-Key": token}
            for task in range(3):
                assignments = request("GET", root + "/tasks", headers=headers).json()
                if len(assignments) != 1 or assignments[0]["task"] != task:
                    raise RuntimeError("Adaptive assignment failed")
                request("POST", root + "/responses", 201, json={"task": task, "chosen": 0}, headers=headers)
            if request("GET", root + "/tasks", headers=headers).json():
                raise RuntimeError("Task limit was exceeded")
            request("DELETE", root + "/participant", 204, headers=headers)
            result = {"status": "passed", "database": health["database"], "initial_training_status": initial,
                      "trained_status": run["status"], "adaptive_tasks": 3, "image_upload": "passed",
                      "pdf_download": "passed", "notifications": len(request("GET", "/notifications").json())}
            print(json.dumps(result, indent=2))
            return result
        finally:
            if project_id:
                request("DELETE", "/projects/" + project_id, 204)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--require-queue", action="store_true")
    args = parser.parse_args()
    smoke(args.url, args.require_queue)
