"""Evaluate repeated hypothetical pricing answers in the CC BY 4.0 US panel."""
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from download_datasets import TWIN_FILES, download, update
from train_all import ARTIFACTS, RESULTS, SEED, fingerprint, track, write_json


def evaluate():
    paths = download("twin2k")
    catalogue = json.loads((paths / TWIN_FILES[0]).read_text(encoding="utf-8"))
    earlier, later = [pd.read_csv(paths / name) for name in TWIN_FILES[1:]]
    for frame in (earlier, later):
        if frame["pid"].isna().any() or frame["pid"].duplicated().any():
            raise ValueError("Expected unique panel identifiers within each wave table")
    update("twin2k", records=len(later), columns={"waves_1_to_3": len(earlier.columns), "wave_4": len(later.columns)},
           dtypes={name: frame.dtypes.value_counts().rename(index=str).to_dict()
                   for name, frame in (("waves_1_to_3", earlier), ("wave_4", later))},
           missing={"waves_1_to_3": int(earlier.isna().sum().sum()), "wave_4": int(later.isna().sum().sum())})
    questions = sorted(q["QuestionID"] for q in catalogue if q.get("BlockName", "").strip() == "Product Preferences - Pricing"
                       and q.get("Options") == ["Yes, I would purchase the product", "No, I would not purchase the product"]
                       and q["QuestionID"] in earlier and q["QuestionID"] in later)
    if not questions:
        raise ValueError("The documented pricing items are missing from the response tables")
    paired = earlier[["pid", *questions]].merge(later[["pid", *questions]], on="pid",
                                                  suffixes=("_earlier", "_later"), validate="one_to_one").sort_values("pid")
    held = np.random.default_rng(SEED).permutation(len(paired))[:len(paired) // 5]
    test_mask = np.zeros(len(paired), dtype=bool)
    test_mask[held] = True
    actual, pooled, personal, person_rows = [], [], [], []
    parameters = {}
    for q in questions:
        prev, next_ = paired[q + "_earlier"], paired[q + "_later"]
        observed = prev.isin([1, 2]).to_numpy() & next_.isin([1, 2]).to_numpy()
        valid_train = observed & ~test_mask
        valid_test = observed & test_mask
        train_yes = next_.eq(1).to_numpy()
        base = (train_yes[valid_train].sum() + 1) / (valid_train.sum() + 2)
        transition = {}
        for code in (1, 2):
            group = valid_train & prev.eq(code).to_numpy()
            transition[str(code)] = float((train_yes[group].sum() + 10 * base) / (group.sum() + 10))
        parameters[q] = {"base": float(base), "given_previous_code": transition}
        actual.extend(train_yes[valid_test].astype(int))
        pooled.extend([base] * int(valid_test.sum()))
        personal.extend(transition[str(int(code))] for code in prev[valid_test])
        person_rows.extend(paired.index[valid_test])
    y, base, individual = np.asarray(actual), np.asarray(pooled), np.asarray(personal)
    scores = {}
    for name, probability in (("question_marginal", base), ("prior_answer_transition", individual)):
        scores[name] = {
            "log_loss": log_loss(y, probability), "brier": brier_score_loss(y, probability),
            "accuracy": accuracy_score(y, probability >= 0.5), "roc_auc": roc_auc_score(y, probability),
        }
    squared_error_delta = pd.Series((individual - y) ** 2 - (base - y) ** 2).groupby(person_rows).mean().to_numpy()
    rng = np.random.default_rng(SEED + 1)
    bootstrap = rng.choice(squared_error_delta, size=(2000, len(squared_error_delta)), replace=True).mean(axis=1)
    source_fingerprints = {name: fingerprint(paths / name) for name in TWIN_FILES}
    dataset_version = hashlib.sha256(json.dumps(source_fingerprints, sort_keys=True).encode()).hexdigest()
    model = ARTIFACTS / "twin2k/pricing_transitions.json"
    report = RESULTS / "twin2k_pricing_fidelity.json"
    result = {
        "source": "Twin-2K-500, CC BY 4.0", "source_url": "https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500",
        "dataset_version": dataset_version, "files_sha256": source_fingerprints,
        "target": "Wave 4 self-reported hypothetical purchase answer on repeated pricing questions",
        "split": "held-out participants, trained on other participants' earlier and Wave 4 answers",
        "train_participants": int((~test_mask).sum()), "test_participants": int(test_mask.sum()), "test_rows": len(y),
        "questions": len(questions), "seed": SEED, "trained_at": datetime.now(timezone.utc).isoformat(), "metrics": scores,
        "participant_mean_brier_difference_ci_95": np.quantile(bootstrap, [0.025, 0.975]).tolist(),
        "limitations": "US survey test-retest on repeated items. Hypothetical answer prediction, with no Indian market or revealed purchase validation.",
    }
    write_json(model, {"dataset_version": dataset_version, "parameters": parameters})
    write_json(report, result)
    track("DemandTwin / Twin-2K-500 pricing fidelity", result, [report, model])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    evaluate()
