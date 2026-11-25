"""Acquire vetted sources with resumable transfers and a local manifest."""
import argparse
import hashlib
import json
import os
import csv
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile, is_zipfile

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "data/metadata/dataset_catalogue.json"
RETAIL_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
OFF_URL = (
    "https://world.openfoodfacts.org/api/v2/search?countries_tags_en=india&categories_tags_en=snacks"
    "&page_size=100&fields=code,product_name,brands,ingredients_text,categories_tags,nutriments,packaging,quantity,countries_tags"
)
TWIN_BASE = "https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500/resolve/main/question_catalog_and_human_response_csv/"
TWIN_FILES = ("question_catalog.json", "wave1_3_response.csv", "wave4_response.csv")


def update(dataset, **changes):
    entries = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    next(row for row in entries if row["id"] == dataset).update(changes)
    temp = CATALOGUE.with_suffix(".tmp")
    temp.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(CATALOGUE)


def validate(path, dataset):
    if dataset == "online_retail":
        if not is_zipfile(path):
            raise ValueError("UCI download is not a ZIP archive")
        with ZipFile(path) as archive:
            if "Online Retail.xlsx" not in archive.namelist() or archive.testzip() is not None:
                raise ValueError("UCI archive is incomplete or corrupt")
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload.get("products"), list) or not payload["products"]:
            raise ValueError("Open Food Facts returned no usable products")


def transfer(path, url, agent, check, resume=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        partial = path.with_suffix(path.suffix + ".part")
        offset = partial.stat().st_size if partial.exists() and resume else 0
        headers = {"User-Agent": agent}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        from urllib.error import HTTPError
        try:
            response = urlopen(Request(url, headers=headers), timeout=45)
        except HTTPError as exc:
            if exc.code != 416 or not offset:
                raise
            check(partial)
            partial.replace(path)
        else:
            with response:
                append = response.status == 206
                if append and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise ValueError("Unexpected range in resumed download")
                with partial.open("ab" if append else "wb") as output:
                    while block := response.read(1024 * 1024):
                        output.write(block)
            try:
                check(partial)
            except (ValueError, OSError):
                partial.unlink(missing_ok=True)
                raise
            partial.replace(path)
    check(path)
    with path.open("rb") as source:
        sha256 = hashlib.file_digest(source, "sha256").hexdigest()
    print(f"{path.name}: {path.stat().st_size:,} bytes, sha256 {sha256}")
    return {"bytes": path.stat().st_size, "sha256": sha256, "download_url": url}


def validate_twin(path):
    if path.name.endswith((".json", ".json.part")):
        questions = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(questions, list) or not questions or not all(isinstance(row, dict) and "QuestionID" in row for row in questions):
            raise ValueError("Invalid Twin-2K-500 question catalogue")
    else:
        with path.open(encoding="utf-8-sig", newline="") as file:
            rows = csv.reader(file)
            header = next(rows, [])
            if not header or header[0] != "pid" or not any(column.startswith("QID9_") for column in header):
                raise ValueError("Invalid Twin-2K-500 response header")
            if any(len(row) != len(header) for row in rows):
                raise ValueError("Incomplete Twin-2K-500 response row")


def download(dataset):
    if dataset == "twin2k":
        paths = ROOT / "data/raw/twin2k"
        files = {name: transfer(paths / name, TWIN_BASE + name, "DemandTwin/0.1", validate_twin) for name in TWIN_FILES}
        update(dataset, files=list(files), file_metadata=files, bytes=sum(item["bytes"] for item in files.values()),
               access_date=date.today().isoformat(), download_status="downloaded numeric response subset and catalogue")
        return paths
    if dataset == "online_retail":
        url, filename, agent = RETAIL_URL, "online_retail.zip", "DemandTwin/0.1"
    else:
        agent = os.getenv("OFF_USER_AGENT")
        if not agent:
            raise ValueError("Set OFF_USER_AGENT to DemandTwin/0.1 followed by your project URL or contact")
        url, filename = OFF_URL, "india_snacks.json"
    path = ROOT / "data/raw" / dataset / filename
    metadata = transfer(path, url, agent, lambda item: validate(item, dataset), resume=dataset == "online_retail")
    update(dataset, download_status="downloaded and format verified", access_date=date.today().isoformat(), **metadata)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", nargs="?", default="online_retail", choices=["online_retail", "off_india", "twin2k"])
    args = parser.parse_args()
    try:
        download(args.dataset)
    except (OSError, ValueError) as exc:
        update(args.dataset, download_status=f"download failed: {type(exc).__name__}")
        parser.exit(1, f"{args.dataset}: {exc}\n")
